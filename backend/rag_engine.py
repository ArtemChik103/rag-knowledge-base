import time
import uuid
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from backend.config import settings
from backend.document_parser import DocumentParser, ParsedDocument
from backend.text_splitter import RecursiveTextSplitter, DocumentChunk
from backend.vector_store import VectorStore, SearchResult

class Citation(BaseModel):
    chunk_id: str
    filename: str
    page_number: Optional[int] = None
    chunk_index: int
    score: float
    snippet: str

class QueryResponse(BaseModel):
    query: str
    answer: str
    citations: List[Citation]
    confidence_score: float
    retrieval_time_ms: float
    generation_time_ms: float
    total_time_ms: float
    retrieved_chunks_count: int

class RAGEngine:
    def __init__(self, vector_store: Optional[VectorStore] = None):
        self.vector_store = vector_store or VectorStore()
        self.splitter = RecursiveTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP
        )

    def ingest_file(self, file_path: Path | str, original_filename: str, doc_id: Optional[str] = None) -> Dict[str, Any]:
        # Deduplicate: if a document with the exact same filename already exists, remove previous version first
        existing_docs = self.vector_store.list_documents()
        for d in existing_docs:
            if d.get("filename") == original_filename:
                self.vector_store.delete_document(d["doc_id"])

        doc_id = doc_id or str(uuid.uuid4())
        
        # 1. Parse document
        parsed_doc = DocumentParser.parse_file(file_path, doc_id=doc_id, original_filename=original_filename)
        
        # 2. Split into chunks
        chunks = self.splitter.split_document(parsed_doc)
        
        # 3. Store in vector DB
        chunks_added = self.vector_store.add_chunks(chunks)

        return {
            "doc_id": doc_id,
            "filename": original_filename,
            "file_type": parsed_doc.file_type,
            "total_pages": parsed_doc.total_pages,
            "total_chars": parsed_doc.total_chars,
            "total_chunks": chunks_added,
        }

    def _generate_with_openai(self, query: str, context_chunks: List[SearchResult]) -> Optional[str]:
        if not settings.OPENAI_API_KEY:
            return None
        
        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_API_BASE or None,
            )

            context_text = "\n\n".join([
                f"[Источник: {c.filename}, Стр. {c.page_number or 1}, Фрагмент {c.chunk_index}]:\n{c.text}"
                for c in context_chunks
            ])

            system_prompt = (
                "Ты — экспертная поисковая система по корпоративной базе знаний и регламентам. "
                "Отвечай на вопрос пользователя исключительно на основе приведенного контекста. "
                "Ответ должен быть точным, структурированным, кратким и не содержать выдуманных фактов. "
                "Если в контексте нет ответа на вопрос, прямо напиши: 'В предоставленных документах нет информации по данному вопросу.' "
                "Обязательно ссылайся на номера страниц и названия регламентов при наличии."
            )

            user_prompt = f"Контекст из базы знаний:\n{context_text}\n\nВопрос пользователя: {query}\n\nОтвет:"

            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                max_tokens=800,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            # Fall back to local grounded synthesizer
            return None

    def _generate_grounded_local_answer(self, query: str, context_chunks: List[SearchResult]) -> str:
        """Deterministic, grounded local answer extraction from top retrieved chunks."""
        if not context_chunks:
            return "В базе знаний нет релевантных документов для ответа на этот вопрос. Пожалуйста, загрузите документ (например, регламент компании) для выполнения поиска."

        # Extract keywords from query
        clean_q = re.sub(r"[^\w\sа-яА-ЯёЁ]", " ", query.lower())
        stopwords = {
            "каков", "какой", "какая", "какие", "каком", "что", "где", "когда", "кто", "чем",
            "как", "почему", "зачем", "сколько", "ли", "или", "для", "при", "по", "из", "на", "в",
            "о", "об", "обо", "под", "над", "от", "до", "без", "после", "есть", "быть", "ли", "это"
        }
        query_terms = [w for w in clean_q.split() if len(w) > 2 and w not in stopwords]

        # Extract and rank sentences from all retrieved chunks
        scored_sentences = []
        for chunk in context_chunks:
            # Split into sentences
            raw_sents = re.split(r"(?<=[.!?])\s+", chunk.text)
            for s in raw_sents:
                clean_s = s.strip()
                if len(clean_s) < 15:
                    continue
                s_lower = clean_s.lower()
                
                # Match query terms
                matches = sum(1 for t in query_terms if t in s_lower or any(t[:4] in w for w in s_lower.split()))
                if matches > 0 or len(scored_sentences) < 3:
                    score = (matches * 2.0) + chunk.score
                    scored_sentences.append({
                        "sentence": clean_s,
                        "score": score,
                        "page": chunk.page_number,
                        "filename": chunk.filename
                    })

        # Sort sentences by match score
        scored_sentences.sort(key=lambda x: x["score"], reverse=True)

        if not scored_sentences:
            # Fallback to presenting top chunk text
            top_chunk = context_chunks[0]
            page_info = f" (стр. {top_chunk.page_number})" if top_chunk.page_number else ""
            return f"Согласно документу «{top_chunk.filename}»{page_info}:\n\n{top_chunk.text}"

        # Group top 3-4 distinct sentences
        selected = []
        seen = set()
        for item in scored_sentences:
            st = item["sentence"]
            if st not in seen:
                seen.add(st)
                selected.append(item)
                if len(selected) >= 3:
                    break

        top_chunk = context_chunks[0]
        page_info = f" (стр. {top_chunk.page_number})" if top_chunk.page_number else ""
        
        answer_parts = []
        answer_parts.append(f"На основе анализа базы знаний («{top_chunk.filename}»{page_info}):\n")
        
        for item in selected:
            p_str = f" [Стр. {item['page']}]" if item['page'] else ""
            answer_parts.append(f"• {item['sentence']}{p_str}")

        return "\n".join(answer_parts)

    def query(self, query_text: str, top_k: int = settings.TOP_K, doc_id: Optional[str] = None) -> QueryResponse:
        start_total = time.perf_counter()
        
        # 1. Retrieval
        start_retrieval = time.perf_counter()
        retrieved_chunks = self.vector_store.search(query=query_text, top_k=top_k, doc_id=doc_id)
        retrieval_time_ms = (time.perf_counter() - start_retrieval) * 1000.0

        # Filter by threshold if we have results
        valid_chunks = [c for c in retrieved_chunks if c.score >= settings.SIMILARITY_THRESHOLD]
        if not valid_chunks and retrieved_chunks:
            # Keep top 1 if confidence is marginally below threshold
            if retrieved_chunks[0].score >= 0.15:
                valid_chunks = [retrieved_chunks[0]]

        # 2. Generation / Synthesis
        start_generation = time.perf_counter()
        if not valid_chunks:
            answer = "По вашему запросу в загруженных документах не найдено релевантной информации. Попробуйте уточнить формулировку или загрузить регламент."
            confidence = 0.0
            citations = []
        else:
            # Try LLM if configured, else use grounded local synthesizer
            llm_answer = self._generate_with_openai(query_text, valid_chunks)
            if llm_answer:
                answer = llm_answer
            else:
                answer = self._generate_grounded_local_answer(query_text, valid_chunks)

            confidence = round(valid_chunks[0].score, 4)
            citations = [
                Citation(
                    chunk_id=c.chunk_id,
                    filename=c.filename,
                    page_number=c.page_number,
                    chunk_index=c.chunk_index,
                    score=c.score,
                    snippet=c.text[:280] + ("..." if len(c.text) > 280 else "")
                )
                for c in valid_chunks
            ]

        generation_time_ms = (time.perf_counter() - start_generation) * 1000.0
        total_time_ms = (time.perf_counter() - start_total) * 1000.0

        return QueryResponse(
            query=query_text,
            answer=answer,
            citations=citations,
            confidence_score=confidence,
            retrieval_time_ms=round(retrieval_time_ms, 2),
            generation_time_ms=round(generation_time_ms, 2),
            total_time_ms=round(total_time_ms, 2),
            retrieved_chunks_count=len(valid_chunks)
        )
