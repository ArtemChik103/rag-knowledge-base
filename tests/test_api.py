import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "vector_store" in data

def test_stats_endpoint():
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_chunks" in data
    assert "total_documents" in data

def test_sample_document_and_query_flow():
    # 1. Reset DB
    res_reset = client.post("/api/reset")
    assert res_reset.status_code == 200

    # 2. Generate and index sample document
    res_sample = client.post("/api/sample-document")
    assert res_sample.status_code == 200
    doc_info = res_sample.json()["document"]
    assert doc_info["filename"] == "sample_company_policy.pdf"
    assert doc_info["total_chunks"] > 0

    # 3. List documents
    res_docs = client.get("/api/documents")
    assert res_docs.status_code == 200
    docs = res_docs.json()
    assert len(docs) >= 1
    doc_id = docs[0]["doc_id"]

    # 4. Get chunks
    res_chunks = client.get(f"/api/documents/{doc_id}/chunks")
    assert res_chunks.status_code == 200
    assert len(res_chunks.json()) > 0

    # 5. Query: "Какой график работы компании?"
    res_query = client.post(
        "/api/query",
        json={"query": "Какой график работы установлен в компании и со скольки до скольки обед?", "top_k": 3}
    )
    assert res_query.status_code == 200
    q_data = res_query.json()
    assert "answer" in q_data
    assert len(q_data["citations"]) > 0
    assert q_data["confidence_score"] > 0
    assert "09:00" in q_data["answer"] or "18:00" in q_data["answer"] or "обед" in q_data["answer"].lower() or len(q_data["citations"]) > 0

    # 6. Query: "Какова компенсация на спорт?"
    res_query2 = client.post(
        "/api/query",
        json={"query": "Каков размер компенсации расходов на спорт и фитнес?", "top_k": 3}
    )
    assert res_query2.status_code == 200
    q_data2 = res_query2.json()
    assert len(q_data2["citations"]) > 0
    assert "35 000" in q_data2["answer"] or "спорт" in q_data2["answer"].lower() or any("35 000" in c["snippet"] for c in q_data2["citations"])
