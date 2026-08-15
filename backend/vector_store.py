import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
from pydantic import BaseModel
import chromadb
from chromadb import EmbeddingFunction, Documents, Embeddings
from chromadb.config import Settings as ChromaSettings
from backend.config import settings
from backend.text_splitter import DocumentChunk

logger = logging.getLogger(__name__)

class SearchResult(BaseModel):
    chunk_id: str
    doc_id: str
    filename: str
    chunk_index: int
    page_number: Optional[int] = None
    text: str
    score: float # Cosine similarity score [0.0 - 1.0, higher is better]
    distance: float # Raw distance (cosine distance)

class MultilingualEmbeddingFunction(EmbeddingFunction[Documents]):
    """High-performance embedding function combining ONNX Runtime, PyTorch inference_mode, and LRU Cache."""
    def __init__(self, model_name: str = settings.EMBEDDING_MODEL):
        self.model_name = model_name
        self.full_hf_name = model_name if "/" in model_name else f"sentence-transformers/{model_name}"
        self._onnx_session = None
        self._tokenizer = None
        self._torch_model = None
        self._fallback_mode = False
        self._cache: Dict[str, List[float]] = {}
        self._max_cache_size = 2048
        self._initialized = False

    def name(self) -> str:
        return f"multilingual_{self.model_name.replace('/', '_')}"

    def get_config(self) -> Dict[str, Any]:
        return {"model_name": self.model_name}

    def _init_engine(self):
        onnx_candidates = [
            settings.BASE_DIR / "models" / "model_quantized.onnx",
            settings.BASE_DIR / "models" / "model.onnx",
        ]
        tokenizer_dir = settings.BASE_DIR / "models" / "tokenizer"
        
        # 1. Try ONNX Runtime first (Fastest C++ inference, 20MB RAM, instant offline startup)
        for onnx_file in onnx_candidates:
            if onnx_file.exists():
                try:
                    import onnxruntime as ort
                    from transformers import AutoTokenizer
                    
                    logger.info(f"Initializing ONNX Runtime with model: {onnx_file}")
                    sess_opts = ort.SessionOptions()
                    sess_opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                    sess_opts.intra_op_num_threads = 1
                    sess_opts.inter_op_num_threads = 1
                    sess_opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
                    
                    self._onnx_session = ort.InferenceSession(
                        str(onnx_file),
                        sess_options=sess_opts,
                        providers=["CPUExecutionProvider"]
                    )
                    tok_src = str(tokenizer_dir) if tokenizer_dir.exists() else self.full_hf_name
                    self._tokenizer = AutoTokenizer.from_pretrained(tok_src, use_fast=True)
                    logger.info(f"ONNX Runtime embedding session ready ({onnx_file.name}).")
                    return
                except Exception as e:
                    logger.warning(f"Failed to load ONNX session from {onnx_file} ({e}), trying next.")


        # 2. Fall back to PyTorch SentenceTransformers with torch.inference_mode()
        try:
            import torch
            from sentence_transformers import SentenceTransformer
            
            cpu_threads = min(2, os.cpu_count() or 1)
            torch.set_num_threads(cpu_threads)

            logger.info(f"Loading PyTorch embedding model: {self.model_name}")
            self._torch_model = SentenceTransformer(self.model_name)
            self._torch_model.eval()
            logger.info("SentenceTransformer loaded with torch.inference_mode optimization.")
        except Exception as e:
            logger.warning(f"Could not load SentenceTransformer ({e}). Initializing dense TF-IDF cosine fallback.")
            self._fallback_mode = True


    def _mean_pooling_numpy(self, last_hidden_state: np.ndarray, attention_mask: np.ndarray) -> np.ndarray:
        input_mask_expanded = np.expand_dims(attention_mask, -1).astype(float)
        sum_embeddings = np.sum(last_hidden_state * input_mask_expanded, axis=1)
        sum_mask = np.clip(np.sum(input_mask_expanded, axis=1), a_min=1e-9, a_max=None)
        unnorm = sum_embeddings / sum_mask
        norms = np.linalg.norm(unnorm, axis=1, keepdims=True)
        return unnorm / np.clip(norms, a_min=1e-9, a_max=None)

    def __call__(self, input: Documents) -> Embeddings:
        if not input:
            return []

        if not self._initialized:
            self._init_engine()
            self._initialized = True

        # 1. Instant O(1) in-memory LRU cache lookup

        cached_results: List[Optional[List[float]]] = [self._cache.get(t) for t in input]
        uncached_indices = [i for i, v in enumerate(cached_results) if v is None]

        if not uncached_indices:
            return [cached_results[i] for i in range(len(input))]  # type: ignore

        uncached_texts = [input[i] for i in uncached_indices]
        new_embeddings: List[List[float]] = []

        # 2. ONNX Runtime execution (if available)
        if self._onnx_session is not None and self._tokenizer is not None:
            try:
                batch_size = 32
                for b_start in range(0, len(uncached_texts), batch_size):
                    b_texts = uncached_texts[b_start : b_start + batch_size]
                    encoded_inputs = self._tokenizer(
                        b_texts,
                        padding=True,
                        truncation=True,
                        max_length=256,
                        return_tensors="np"
                    )
                    
                    ort_inputs = {
                        "input_ids": encoded_inputs["input_ids"],
                        "attention_mask": encoded_inputs["attention_mask"],
                    }
                    if "token_type_ids" in encoded_inputs:
                        ort_inputs["token_type_ids"] = encoded_inputs["token_type_ids"]

                    outputs = self._onnx_session.run(None, ort_inputs)
                    pooled = self._mean_pooling_numpy(outputs[0], encoded_inputs["attention_mask"])
                    new_embeddings.extend([row.tolist() for row in pooled])
            except Exception as e:
                logger.error(f"ONNX inference error: {e}. Falling back to PyTorch.")
                new_embeddings = []

        # 3. PyTorch SentenceTransformers execution (if ONNX didn't run)
        if not new_embeddings and self._torch_model is not None and not self._fallback_mode:
            try:
                import torch
                with torch.inference_mode():
                    raw_emb = self._torch_model.encode(
                        uncached_texts,
                        batch_size=32,
                        normalize_embeddings=True,
                        show_progress_bar=False
                    )
                    new_embeddings = [emb.tolist() for emb in raw_emb]
            except Exception as e:
                logger.error(f"PyTorch inference error: {e}. Using deterministic dense fallback.")

        # 4. Dense semantic fallback (if dependencies are unavailable)
        if not new_embeddings:
            import math
            import hashlib
            dim = 384
            for text in uncached_texts:
                vec = [0.0] * dim
                words = text.lower().split()
                if not words:
                    words = [text.lower()]
                for word in words:
                    h = int(hashlib.md5(word.encode('utf-8')).hexdigest(), 16)
                    idx = h % dim
                    sign = 1.0 if (h >> 8) % 2 == 0 else -1.0
                    vec[idx] += sign
                    for i in range(len(word) - 2):
                        tri = word[i:i+3]
                        ht = int(hashlib.md5(tri.encode('utf-8')).hexdigest(), 16)
                        vec[ht % dim] += 0.5 * (1.0 if (ht >> 8) % 2 == 0 else -1.0)
                norm = math.sqrt(sum(x * x for x in vec)) or 1.0
                new_embeddings.append([x / norm for x in vec])

        # 5. Populate LRU cache
        if len(self._cache) > self._max_cache_size:
            self._cache = dict(list(self._cache.items())[self._max_cache_size // 2:])

        for idx, text, emb in zip(uncached_indices, uncached_texts, new_embeddings):
            self._cache[text] = emb
            cached_results[idx] = emb

        return [cached_results[i] for i in range(len(input))]  # type: ignore


class VectorStore:
    def __init__(self, persist_dir: Path | str = settings.DATA_DIR, collection_name: str = settings.COLLECTION_NAME):
        self.persist_dir = Path(persist_dir)
        self.collection_name = collection_name
        self.embedding_fn = MultilingualEmbeddingFunction()
        
        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        self._get_or_create_collection()

    def _get_or_create_collection(self):
        try:
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_fn,
                metadata={"hnsw:space": "cosine"}
            )
        except Exception as e:
            logger.warning(f"Collection mismatch or corruption ({e}), recreating clean collection.")
            try:
                self.client.delete_collection(self.collection_name)
            except Exception:
                pass
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_fn,
                metadata={"hnsw:space": "cosine"}
            )


    def add_chunks(self, chunks: List[DocumentChunk]) -> int:
        if not chunks:
            return 0

        ids = [c.chunk_id for c in chunks]
        documents = [c.text for c in chunks]
        metadatas = [
            {
                "doc_id": c.doc_id,
                "filename": c.filename,
                "chunk_index": c.chunk_index,
                "page_number": c.page_number if c.page_number is not None else -1,
                "char_count": c.char_count,
                "start_char": c.start_char,
                "end_char": c.end_char,
            }
            for c in chunks
        ]

        batch_size = 100
        total = len(ids)
        for i in range(0, total, batch_size):
            end = min(i + batch_size, total)
            self.collection.upsert(
                ids=ids[i:end],
                documents=documents[i:end],
                metadatas=metadatas[i:end]
            )

        return total

    def search(self, query: str, top_k: int = settings.TOP_K, doc_id: Optional[str] = None) -> List[SearchResult]:
        if not query.strip() or self.collection.count() == 0:
            return []

        where_filter = {"doc_id": doc_id} if doc_id else None
        
        total_count = self.collection.count()
        actual_k = min(top_k, total_count)
        if actual_k <= 0:
            return []

        results = self.collection.query(
            query_texts=[query],
            n_results=actual_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )

        search_results: List[SearchResult] = []
        if not results or not results["ids"] or not results["ids"][0]:
            return []

        ids = results["ids"][0]
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        distances = results["distances"][0]

        for chunk_id, text, meta, dist in zip(ids, docs, metas, distances):
            similarity = max(0.0, min(1.0, 1.0 - (dist / 2.0 if dist > 1.0 else dist)))
            
            page_num = meta.get("page_number")
            if page_num == -1:
                page_num = None

            search_results.append(
                SearchResult(
                    chunk_id=chunk_id,
                    doc_id=meta.get("doc_id", ""),
                    filename=meta.get("filename", ""),
                    chunk_index=meta.get("chunk_index", 0),
                    page_number=page_num,
                    text=text,
                    score=round(similarity, 4),
                    distance=round(dist, 4),
                )
            )

        search_results.sort(key=lambda x: x.score, reverse=True)
        return search_results

    def list_documents(self) -> List[Dict[str, Any]]:
        total = self.collection.count()
        if total == 0:
            return []

        all_records = self.collection.get(include=["metadatas"])
        metadatas = all_records.get("metadatas", [])

        docs_map: Dict[str, Dict[str, Any]] = {}
        for m in metadatas:
            if not m:
                continue
            doc_id = m.get("doc_id")
            if not doc_id:
                continue

            if doc_id not in docs_map:
                docs_map[doc_id] = {
                    "doc_id": doc_id,
                    "filename": m.get("filename", "unknown"),
                    "chunk_count": 0,
                    "pages": set(),
                    "total_chars": 0,
                }
            docs_map[doc_id]["chunk_count"] += 1
            docs_map[doc_id]["total_chars"] += m.get("char_count", 0)
            page = m.get("page_number")
            if page and page != -1:
                docs_map[doc_id]["pages"].add(page)

        result = []
        for doc_id, data in docs_map.items():
            result.append({
                "doc_id": doc_id,
                "filename": data["filename"],
                "chunk_count": data["chunk_count"],
                "total_pages": len(data["pages"]) if data["pages"] else 1,
                "total_chars": data["total_chars"],
            })

        return sorted(result, key=lambda x: x["filename"])

    def get_document_chunks(self, doc_id: str) -> List[Dict[str, Any]]:
        records = self.collection.get(
            where={"doc_id": doc_id},
            include=["documents", "metadatas"]
        )
        if not records or not records["ids"]:
            return []

        chunks = []
        for cid, doc, meta in zip(records["ids"], records["documents"], records["metadatas"]):
            page = meta.get("page_number")
            chunks.append({
                "chunk_id": cid,
                "chunk_index": meta.get("chunk_index", 0),
                "page_number": page if page != -1 else None,
                "text": doc,
                "char_count": meta.get("char_count", len(doc)),
            })
        
        return sorted(chunks, key=lambda x: x["chunk_index"])

    def delete_document(self, doc_id: str) -> bool:
        try:
            self.collection.delete(where={"doc_id": doc_id})
            return True
        except Exception as e:
            logger.error(f"Error deleting document {doc_id}: {e}")
            return False

    def reset(self) -> bool:
        try:
            self.client.delete_collection(self.collection_name)
            self._get_or_create_collection()
            return True
        except Exception as e:
            logger.error(f"Error resetting collection: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        docs = self.list_documents()
        total_chunks = self.collection.count()
        engine_name = "ONNXRuntime" if self.embedding_fn._onnx_session else ("PyTorch" if self.embedding_fn._torch_model else "Fallback")
        return {
            "total_documents": len(docs),
            "total_chunks": total_chunks,
            "collection_name": self.collection_name,
            "embedding_model": self.embedding_fn.model_name,
            "engine": engine_name,
            "cache_entries": len(self.embedding_fn._cache),
            "is_fallback_embedding": self.embedding_fn._fallback_mode,
        }
