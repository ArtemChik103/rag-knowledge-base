import re
from typing import List, Optional
from pydantic import BaseModel
from backend.document_parser import ParsedDocument

class DocumentChunk(BaseModel):
    chunk_id: str
    doc_id: str
    filename: str
    chunk_index: int
    page_number: Optional[int] = None
    text: str
    char_count: int
    start_char: int
    end_char: int

class RecursiveTextSplitter:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100):
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be strictly less than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " "]

    def _split_text_recursive(self, text: str, separators: List[str]) -> List[str]:
        if len(text) <= self.chunk_size or not separators:
            return [text] if text.strip() else []

        sep = separators[0]
        remaining_seps = separators[1:]

        if sep in text:
            splits = text.split(sep)
            chunks: List[str] = []
            current_chunk: List[str] = []
            current_len = 0

            for part in splits:
                part_with_sep = part + (sep if sep != text else "")
                part_len = len(part_with_sep)

                if part_len > self.chunk_size:
                    # Если этот фрагмент сам по себе превышает chunk_size, рекурсивно разбиваем его
                    if current_chunk:
                        joined = sep.join(current_chunk).strip()
                        if joined:
                            chunks.append(joined)
                        current_chunk = []
                        current_len = 0
                    
                    sub_chunks = self._split_text_recursive(part, remaining_seps)
                    chunks.extend(sub_chunks)
                elif current_len + part_len <= self.chunk_size:
                    current_chunk.append(part)
                    current_len += part_len
                else:
                    joined = sep.join(current_chunk).strip()
                    if joined:
                        chunks.append(joined)
                    current_chunk = [part]
                    current_len = part_len

            if current_chunk:
                joined = sep.join(current_chunk).strip()
                if joined:
                    chunks.append(joined)

            return chunks
        else:
            return self._split_text_recursive(text, remaining_seps)

    def _create_overlapping_chunks(self, pieces: List[str]) -> List[str]:
        if not pieces:
            return []

        merged_chunks: List[str] = []
        current = ""

        for piece in pieces:
            piece = piece.strip()
            if not piece:
                continue

            if not current:
                current = piece
            elif len(current) + len(piece) + 1 <= self.chunk_size:
                current = f"{current} {piece}"
            else:
                merged_chunks.append(current)
                # Сохраняем перекрытие (overlap) с конца текущего чанка
                if self.chunk_overlap > 0 and len(current) > self.chunk_overlap:
                    overlap_text = current[-self.chunk_overlap:].strip()
                    # Ищем границу слова в зоне перекрытия
                    space_idx = overlap_text.find(" ")
                    if space_idx != -1 and space_idx < len(overlap_text) - 1:
                        overlap_text = overlap_text[space_idx + 1:]
                    current = f"{overlap_text} {piece}" if overlap_text else piece
                else:
                    current = piece

        if current and (not merged_chunks or merged_chunks[-1] != current):
            merged_chunks.append(current)

        return merged_chunks

    def split_document(self, parsed_doc: ParsedDocument) -> List[DocumentChunk]:
        chunks: List[DocumentChunk] = []
        global_chunk_idx = 0

        for page in parsed_doc.pages:
            page_text = page.text.strip()
            if not page_text:
                continue

            # Разбиение текста страницы
            raw_splits = self._split_text_recursive(page_text, self.separators)
            page_chunks = self._create_overlapping_chunks(raw_splits)

            char_offset = 0
            for chunk_text in page_chunks:
                clean_chunk = chunk_text.strip()
                if not clean_chunk:
                    continue

                chunk_len = len(clean_chunk)
                start_char = page_text.find(clean_chunk, char_offset)
                if start_char == -1:
                    start_char = char_offset
                end_char = start_char + chunk_len
                char_offset = max(char_offset, end_char - self.chunk_overlap)

                chunk_id = f"{parsed_doc.doc_id}_{page.page_number}_{global_chunk_idx}"
                
                chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_id,
                        doc_id=parsed_doc.doc_id,
                        filename=parsed_doc.filename,
                        chunk_index=global_chunk_idx,
                        page_number=page.page_number,
                        text=clean_chunk,
                        char_count=chunk_len,
                        start_char=start_char,
                        end_char=end_char,
                    )
                )
                global_chunk_idx += 1

        return chunks
