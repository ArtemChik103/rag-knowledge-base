import pytest
from pathlib import Path
from backend.document_parser import DocumentParser
from backend.text_splitter import RecursiveTextSplitter

def test_recursive_splitter(tmp_path: Path):
    txt_file = tmp_path / "long_doc.txt"
    paragraphs = [
        "Раздел 1. Общие положения о внутреннем распорядке организации.",
        "Пункт 1.1. Настоящий регламент определяет порядок взаимодействия подразделений.",
        "Пункт 1.2. Каждый сотрудник обязан соблюдать требования охраны труда и техники безопасности.",
        "Пункт 1.3. Прибытие на рабочее место фиксируется автоматической пропускной системой.",
        "Раздел 2. Порядок предоставления отпусков и компенсационных выплат сотрудникам.",
    ]
    txt_file.write_text("\n\n".join(paragraphs), encoding="utf-8")

    parsed = DocumentParser.parse_file(txt_file, doc_id="doc-split", original_filename="long_doc.txt")
    splitter = RecursiveTextSplitter(chunk_size=120, chunk_overlap=30)
    chunks = splitter.split_document(parsed)

    assert len(chunks) > 1
    assert all(c.doc_id == "doc-split" for c in chunks)
    assert all(c.filename == "long_doc.txt" for c in chunks)
    assert all(c.char_count <= 150 for c in chunks) # allow slight margin for clean boundary
    assert chunks[0].page_number == 1

def test_invalid_overlap_raises():
    with pytest.raises(ValueError):
        RecursiveTextSplitter(chunk_size=100, chunk_overlap=100)
