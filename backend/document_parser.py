import os
from pathlib import Path
from typing import List, Dict, Any
from pydantic import BaseModel
import pypdf

class DocumentPage(BaseModel):
    page_number: int
    text: str
    char_count: int

class ParsedDocument(BaseModel):
    doc_id: str
    filename: str
    file_type: str
    total_pages: int
    total_chars: int
    pages: List[DocumentPage]
    raw_text: str

class DocumentParser:
    @staticmethod
    def parse_pdf(file_path: Path | str, doc_id: str, filename: str) -> ParsedDocument:
        path = Path(file_path)
        pages_data: List[DocumentPage] = []
        full_text_parts: List[str] = []

        reader = pypdf.PdfReader(str(path))
        total_pages = len(reader.pages)

        for idx, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            # Clean and normalize excessive whitespace while preserving structure
            lines = [line.strip() for line in page_text.splitlines() if line.strip()]
            cleaned_text = "\n".join(lines)
            
            pages_data.append(
                DocumentPage(
                    page_number=idx,
                    text=cleaned_text,
                    char_count=len(cleaned_text),
                )
            )
            if cleaned_text:
                full_text_parts.append(f"--- [Страница {idx}] ---\n{cleaned_text}")

        raw_text = "\n\n".join(full_text_parts)
        total_chars = sum(p.char_count for p in pages_data)

        return ParsedDocument(
            doc_id=doc_id,
            filename=filename,
            file_type="pdf",
            total_pages=total_pages,
            total_chars=total_chars,
            pages=pages_data,
            raw_text=raw_text,
        )

    @staticmethod
    def parse_text(file_path: Path | str, doc_id: str, filename: str, file_type: str = "txt") -> ParsedDocument:
        path = Path(file_path)
        content = path.read_text(encoding="utf-8", errors="replace")
        
        # Clean lines
        lines = [line.rstrip() for line in content.splitlines()]
        cleaned_text = "\n".join(lines).strip()
        
        page = DocumentPage(
            page_number=1,
            text=cleaned_text,
            char_count=len(cleaned_text),
        )

        return ParsedDocument(
            doc_id=doc_id,
            filename=filename,
            file_type=file_type,
            total_pages=1,
            total_chars=len(cleaned_text),
            pages=[page],
            raw_text=cleaned_text,
        )

    @classmethod
    def parse_file(cls, file_path: Path | str, doc_id: str, original_filename: str) -> ParsedDocument:
        path = Path(file_path)
        ext = path.suffix.lower()

        if ext == ".pdf":
            return cls.parse_pdf(path, doc_id, original_filename)
        elif ext in [".txt", ".md", ".markdown", ".json", ".csv"]:
            return cls.parse_text(path, doc_id, original_filename, file_type=ext.lstrip("."))
        else:
            # Fallback to plain text
            return cls.parse_text(path, doc_id, original_filename, file_type=ext.lstrip(".") or "unknown")
