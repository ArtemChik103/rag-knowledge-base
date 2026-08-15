import pytest
from pathlib import Path
from backend.document_parser import DocumentParser

def test_parse_text_file(tmp_path: Path):
    txt_file = tmp_path / "test_doc.txt"
    content = "Раздел 1. График работы компании.\nРабочее время с 09:00 до 18:00.\nОбед с 13:00 до 14:00."
    txt_file.write_text(content, encoding="utf-8")

    parsed = DocumentParser.parse_file(txt_file, doc_id="doc-123", original_filename="test_doc.txt")
    assert parsed.doc_id == "doc-123"
    assert parsed.filename == "test_doc.txt"
    assert parsed.file_type == "txt"
    assert parsed.total_pages == 1
    assert "09:00" in parsed.raw_text
    assert len(parsed.pages) == 1
    assert parsed.pages[0].char_count > 0

def test_parse_markdown_file(tmp_path: Path):
    md_file = tmp_path / "policy.md"
    content = "# Корпоративная политика\n\n## Информационная безопасность\nПароли меняются каждые 90 дней."
    md_file.write_text(content, encoding="utf-8")

    parsed = DocumentParser.parse_file(md_file, doc_id="doc-456", original_filename="policy.md")
    assert parsed.file_type == "md"
    assert parsed.total_pages == 1
    assert "Информационная безопасность" in parsed.raw_text
