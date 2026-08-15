import pytest
from pathlib import Path
from backend.vector_store import VectorStore
from backend.text_splitter import DocumentChunk

def test_vector_store_operations(tmp_path: Path):
    store = VectorStore(persist_dir=tmp_path, collection_name="test_collection")
    
    chunks = [
        DocumentChunk(
            chunk_id="c1",
            doc_id="doc-1",
            filename="policy.txt",
            chunk_index=0,
            page_number=1,
            text="График работы компании с 09:00 до 18:00 с понедельника по пятницу.",
            char_count=66,
            start_char=0,
            end_char=66,
        ),
        DocumentChunk(
            chunk_id="c2",
            doc_id="doc-1",
            filename="policy.txt",
            chunk_index=1,
            page_number=1,
            text="Компенсация расходов на спорт составляет до 35 000 рублей в год.",
            char_count=65,
            start_char=67,
            end_char=132,
        ),
        DocumentChunk(
            chunk_id="c3",
            doc_id="doc-2",
            filename="security.txt",
            chunk_index=0,
            page_number=1,
            text="Пароли пользователей должны содержать не менее 12 символов.",
            char_count=60,
            start_char=0,
            end_char=60,
        ),
    ]

    # Тест добавления чанков
    added = store.add_chunks(chunks)
    assert added == 3

    # Тест статистики
    stats = store.get_stats()
    assert stats["total_chunks"] == 3
    assert stats["total_documents"] == 2

    # Тест векторного поиска
    results = store.search(query="Каков график работы?", top_k=2)
    assert len(results) > 0
    assert results[0].doc_id == "doc-1"
    assert "09:00" in results[0].text

    # Тест списка документов
    docs = store.list_documents()
    assert len(docs) == 2

    # Тест удаления документа
    deleted = store.delete_document("doc-2")
    assert deleted is True
    assert store.get_stats()["total_documents"] == 1

    # Тест полного сброса
    reset_ok = store.reset()
    assert reset_ok is True
    assert store.get_stats()["total_chunks"] == 0
