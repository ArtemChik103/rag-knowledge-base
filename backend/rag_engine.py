import time
import uuid
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel
from backend.config import settings
from backend.document_parser import DocumentParser, ParsedDocument
from backend.text_splitter import RecursiveTextSplitter, DocumentChunk
from backend.vector_store import VectorStore, SearchResult

RUSSIAN_STOPWORDS = {
    "и", "в", "во", "не", "что", "он", "на", "я", "с", "со", "как", "а", "то", "все", "всё",
    "она", "так", "его", "но", "да", "ты", "к", "у", "же", "вы", "за", "бы", "по", "только",
    "ее", "её", "мне", "было", "вот", "от", "меня", "еще", "ещё", "нет", "о", "из", "ему",
    "теперь", "когда", "даже", "ну", "вдруг", "ли", "если", "уже", "или", "ни", "быть", "был",
    "него", "до", "вас", "нибудь", "опять", "уж", "вам", "ведь", "там", "потом", "себя", "ничего",
    "ей", "может", "они", "тут", "где", "есть", "надо", "ней", "для", "мы", "тебя", "их", "чем",
    "была", "сам", "чтоб", "без", "будто", "чего", "раз", "тоже", "себе", "под", "будет", "ж",
    "тогда", "кто", "этот", "того", "потому", "этого", "какой", "совсем", "ним", "здесь", "этом",
    "один", "почти", "мой", "тем", "чтобы", "нее", "неё", "сейчас", "были", "куда", "зачем",
    "всех", "никогда", "можно", "при", "наконец", "два", "об", "другой", "хоть", "после", "над",
    "больше", "тот", "через", "эти", "нас", "про", "всего", "них", "какая", "какие", "каком",
    "каков", "сколько", "расскажи", "напиши", "поясни", "уточни", "скажи", "происходит", "бывает",
    "является", "находится", "находиться"
}

DOMAIN_FILLER_STEMS = {
    "сотрудник", "работник", "компан", "документ", "регламент", "информац"
}

def russian_stem(w: str) -> str:
    w_clean = re.sub(r"[^\wа-яА-ЯёЁ]", "", w.lower().strip())
    if len(w_clean) <= 3:
        return w_clean
    return re.sub(r"(?:иями|ыми|ями|иях|ях|ых|их|ого|его|ому|ему|ыми|ими|ами|ями|ое|ее|ие|ые|ый|ий|ой|ей|ям|ам|ом|ем|ах|ях|ую|юю|ою|ею|а|е|и|й|о|у|ы|ь|ю|я|овав|ивав|ывав|вш|вши|вшись|ться|тся|те|ти|ли|ла|ло|л)+$", "", w_clean)

def extract_meaningful_stems(query: str) -> List[str]:
    raw_words = re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9]+", query.lower())
    meaningful = [w for w in raw_words if len(w) >= 3 and w not in RUSSIAN_STOPWORDS]
    stems = []
    for w in meaningful:
        st = russian_stem(w)
        if len(st) >= 3:
            stems.append(st)
            
    # Filter generic domain words if more specific intent keywords exist
    specific_stems = [s for s in stems if s not in DOMAIN_FILLER_STEMS]
    return specific_stems if specific_stems else stems

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
        existing_docs = self.vector_store.list_documents()
        for d in existing_docs:
            if d.get("filename") == original_filename:
                self.vector_store.delete_document(d["doc_id"])

        doc_id = doc_id or str(uuid.uuid4())
        parsed_doc = DocumentParser.parse_file(file_path, doc_id=doc_id, original_filename=original_filename)
        chunks = self.splitter.split_document(parsed_doc)
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
                "Ответ должен быть точным, структурированным, исчерпывающим и не содержать выдуманных фактов. "
                "Обязательно указывай точные цифры, временные рамки, регламентные процедуры и условия. "
                "Если в контексте нет информации по вопросу, прямо напиши: 'В предоставленных документах нет информации по данному вопросу.' "
                "Обязательно ссылайся на номера страниц при наличии."
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
        except Exception:
            return None

    def _generate_grounded_local_answer(self, query: str, context_chunks: List[SearchResult]) -> str:
        """Precision, intent-focused grounded answer synthesis from top retrieved chunks."""
        if not context_chunks:
            return "В базе знаний нет релевантных документов для ответа на этот вопрос. Пожалуйста, загрузите документ для выполнения поиска."

        query_stems = extract_meaningful_stems(query)

        candidate_blocks = []
        seen_texts = set()

        for chunk in context_chunks:
            raw_lines = [l.strip() for l in chunk.text.split("\n") if l.strip()]
            blocks = []
            
            for line in raw_lines:
                sub_points = re.split(r"(?=(?:^|\s)(?:\d+\.\d+\.|\•)\s+)", line)
                for sp in sub_points:
                    clean_sp = sp.strip()
                    if len(clean_sp) >= 20:
                        blocks.append(clean_sp)

            for b in blocks:
                norm_b = re.sub(r"\s+", " ", b).strip()
                if norm_b in seen_texts:
                    continue
                seen_texts.add(norm_b)

                b_words = [w for w in re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9]+", norm_b.lower()) if len(w) >= 3 and w not in RUSSIAN_STOPWORDS]
                b_stems = set(russian_stem(w) for w in b_words if len(russian_stem(w)) >= 3)
                
                # Robust morphological stem match
                stem_matches = 0
                for qs in query_stems:
                    for bs in b_stems:
                        if qs == bs or (len(qs) >= 4 and len(bs) >= 4 and (bs.startswith(qs[:4]) or qs.startswith(bs[:4]))):
                            stem_matches += 1
                            break

                has_facts = bool(re.search(r"\d{1,2}:\d{2}|\d+\s*(?:руб|мин|час|дн|%|Мбит|Гб|мес|лет|\$|€)", norm_b.lower()))
                fact_bonus = 4.0 if has_facts else 0.0

                if query_stems:
                    score = (stem_matches * 20.0) + fact_bonus + (chunk.score * 3.0)
                else:
                    score = fact_bonus + (chunk.score * 2.0)

                candidate_blocks.append({
                    "text": norm_b,
                    "score": score,
                    "matches": stem_matches,
                    "page": chunk.page_number,
                    "filename": chunk.filename
                })

        # Strict intent filter: if any blocks match query keywords, exclude non-matching noise
        if query_stems and any(cb["matches"] > 0 for cb in candidate_blocks):
            candidate_blocks = [cb for cb in candidate_blocks if cb["matches"] > 0]

        # Rank candidates by relevance score
        candidate_blocks.sort(key=lambda x: x["score"], reverse=True)

        if not candidate_blocks:
            top_chunk = context_chunks[0]
            return f"Согласно документу «{top_chunk.filename}»:\n\n{top_chunk.text}"

        # Select top complementary blocks (up to 3) matching user intent
        selected = []
        for cb in candidate_blocks:
            if any(cb["text"][:35] in s["text"] or s["text"][:35] in cb["text"] for s in selected):
                continue
            selected.append(cb)
            if len(selected) >= 3:
                break

        top_chunk = context_chunks[0]
        lines = [f"На основе базы знаний («{top_chunk.filename}»):\n"]
        for item in selected:
            p_str = f" [Стр. {item['page']}]" if item['page'] else ""
            lines.append(f"• {item['text']}{p_str}")

        return "\n".join(lines)

    def query(self, query_text: str, top_k: int = settings.TOP_K, doc_id: Optional[str] = None) -> QueryResponse:
        start_total = time.perf_counter()
        
        # 1. Retrieval with hybrid re-ranking
        start_retrieval = time.perf_counter()
        query_stems = extract_meaningful_stems(query_text)
        
        fetch_k = min(12, max(top_k * 2, 6))
        raw_chunks = self.vector_store.search(query=query_text, top_k=fetch_k, doc_id=doc_id)
        
        scored_chunks = []
        for c in raw_chunks:
            c_words = [w for w in re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9]+", c.text.lower()) if len(w) >= 3 and w not in RUSSIAN_STOPWORDS]
            c_stems = set(russian_stem(w) for w in c_words if len(russian_stem(w)) >= 3)
            
            stem_hits = 0
            for qs in query_stems:
                for cs in c_stems:
                    if qs == cs or (len(qs) >= 4 and len(cs) >= 4 and (cs.startswith(qs[:4]) or qs.startswith(cs[:4]))):
                        stem_hits += 1
                        break
            
            lexical_boost = 0.50 * (stem_hits / max(len(query_stems), 1)) if query_stems else 0.0
            final_score = min(1.0, (c.score * 0.50) + lexical_boost)
            
            scored_chunks.append((final_score, c))
            
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        retrieved_chunks = [item[1] for item in scored_chunks[:top_k]]
        
        retrieval_time_ms = (time.perf_counter() - start_retrieval) * 1000.0

        # Filter by threshold if we have results
        valid_chunks = [c for c in retrieved_chunks if c.score >= settings.SIMILARITY_THRESHOLD]
        if not valid_chunks and retrieved_chunks:
            if retrieved_chunks[0].score >= 0.15:
                valid_chunks = [retrieved_chunks[0]]

        # 2. Generation / Synthesis
        start_generation = time.perf_counter()
        if not valid_chunks:
            answer = "По вашему запросу в загруженных документах не найдено релевантной информации. Попробуйте уточнить формулировку или загрузить регламент."
            confidence = 0.0
            citations = []
        else:
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
