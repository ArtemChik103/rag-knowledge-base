import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
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
    """High-performance embedding function with torch.inference_mode, LRU cache, and fallback."""
    def __init__(self, model_name: str = settings.EMBEDDING_MODEL):
        self.model_name = model_name
        self._model = None
        self._fallback_mode = False
        self._cache: Dict[str, List[float]] = {}
        self._max_cache_size = 2000
        self._init_model()

    def name(self) -> str:
        return f"multilingual_{self.model_name.replace('/', '_')}"

    def get_config(self) -> Dict[str, Any]:
        return {"model_name": self.model_name}

    def _init_model(self):
        try:
            import torch
            from sentence_transformers import SentenceTransformer
            
            # Configure intra-op threads for optimal CPU SIMD (AVX-512 / AVX2)
            cpu_threads = min(4, os.cpu_count() or 2)
            torch.set_num_threads(cpu_threads)

            logger.info(f"Loading embedding model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
            self._model.eval()
            logger.info("SentenceTransformer model loaded and optimized for fast inference.")
        except Exception as e:
            logger.warning(f"Could not load SentenceTransformer ({e}). Initializing dense TF-IDF cosine fallback.")
            self._fallback_mode = True

    def __call__(self, input: Documents) -> Embeddings:
        if not input:
            return []
        
        # 1. Check in-memory cache for instant O(1) retrieval
        cached_results: List[Optional[List[float]]] = [self._cache.get(t) for t in input]
        uncached_indices = [i for i, v in enumerate(cached_results) if v is None]

        if not uncached_indices:
            return [cached_results[i] for i in range(len(input))]  # type: ignore

        uncached_texts = [input[i] for i in uncached_indices]

        # 2. Compute embeddings with zero-overhead inference
        new_embeddings: List[List[float]] = []
        if self._model is not None and not self._fallback_mode:
            try:
                import torch
                with torch.inference_mode():
                    raw_emb = self._model.encode(
                        uncached_texts,
                        batch_size=32,
                        normalize_embeddings=True,
                        show_progress_bar=False
                    )
                    new_embeddings = [emb.tolist() for emb in raw_emb]
            except Exception as e:
                logger.error(f"Inference error with SentenceTransformer: {e}. Using fallback.")
        
        if not new_embeddings:
            # Fallback dense n-gram calculation
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

        # 3. Store in LRU cache
        if len(self._cache) > self._max_cache_size:
            # Evict oldest entries
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
        return {
            "total_documents": len(docs),
            "total_chunks": total_chunks,
            "collection_name": self.collection_name,
            "embedding_model": self.embedding_fn.model_name,
            "is_fallback_embedding": self.embedding_fn._fallback_mode,
        }
