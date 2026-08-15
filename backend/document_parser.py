import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from pydantic import BaseModel

# Try ultra-fast C-engine PyMuPDF first, fallback to pure-python pypdf
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False
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
    def _extract_page_fitz(page_tuple) -> DocumentPage:
        page_idx, page = page_tuple
        # Extract text blocks directly from MuPDF C-engine (lossless, preserves exact paragraph structure)
        blocks = page.get_text("blocks")
        text_blocks = []
        for b in blocks:
            # b: (x0, y0, x1, y1, text, block_no, block_type) - block_type 0 is text
            if len(b) >= 7 and b[6] == 0:
                raw_block = b[4].strip()
                # Normalize visual line wraps within the block to spaces
                norm_block = " ".join(line.strip() for line in raw_block.splitlines() if line.strip())
                if norm_block:
                    text_blocks.append(norm_block)

        page_text = "\n\n".join(text_blocks).strip()
        return DocumentPage(
            page_number=page_idx,
            text=page_text,
            char_count=len(page_text),
        )

    @staticmethod
    def parse_pdf_pymupdf(file_path: Path | str, doc_id: str, filename: str) -> ParsedDocument:
        doc = fitz.open(str(file_path))
        total_pages = len(doc)

        pages_data = [DocumentParser._extract_page_fitz((i + 1, doc[i])) for i in range(total_pages)]
        doc.close()


        full_text_parts = [f"--- [Страница {p.page_number}] ---\n{p.text}" for p in pages_data if p.text]
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
    def parse_pdf_pypdf(file_path: Path | str, doc_id: str, filename: str) -> ParsedDocument:
        import pypdf
        path = Path(file_path)
        pages_data: List[DocumentPage] = []
        full_text_parts: List[str] = []

        reader = pypdf.PdfReader(str(path))
        total_pages = len(reader.pages)

        for idx, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            lines = [line.strip() for line in page_text.splitlines() if line.strip()]
            
            paragraphs: List[str] = []
            cur_p: List[str] = []
            
            for line in lines:
                is_new_section = bool(re.match(r"^(\d+\.\d+\.|\•|Раздел|ООО|\#|\-|\*|[A-ZА-ЯЁ\d\.\s]{4,}:)", line))
                if is_new_section and cur_p:
                    paragraphs.append(" ".join(cur_p))
                    cur_p = []
                cur_p.append(line)
            if cur_p:
                paragraphs.append(" ".join(cur_p))

            cleaned_text = "\n\n".join(paragraphs).strip()
            
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
    def parse_pdf(file_path: Path | str, doc_id: str, filename: str) -> ParsedDocument:
        if HAS_PYMUPDF:
            try:
                return DocumentParser.parse_pdf_pymupdf(file_path, doc_id, filename)
            except Exception:
                return DocumentParser.parse_pdf_pypdf(file_path, doc_id, filename)
        return DocumentParser.parse_pdf_pypdf(file_path, doc_id, filename)

    @staticmethod
    def parse_text(file_path: Path | str, doc_id: str, filename: str, file_type: str = "txt") -> ParsedDocument:
        path = Path(file_path)
        content = path.read_text(encoding="utf-8", errors="replace")
        
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
            return cls.parse_text(path, doc_id, original_filename, file_type=ext.lstrip(".") or "unknown")
