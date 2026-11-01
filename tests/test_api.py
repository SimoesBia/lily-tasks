import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from lily.api import create_app  # noqa: E402
from tests.helpers import make_runtime  # noqa: E402


@pytest.fixture()
def client():
    rt, clock = make_runtime()
    c = TestClient(create_app(rt))
    c.clock = clock
    return c


def H(sid):
    return {"X-Session-Id": sid}


def new_session(client) -> str:
    return client.post("/sessions").json()["session_id"]


def test_health_reports_demo_mode_without_key(client):
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["mode"] == "demo" and body["model"] is None


def test_requires_valid_session_header(client):
    assert client.get("/tasks").status_code == 422
    assert client.get("/tasks", headers=H("curto")).json()["error"] == "invalid_session"


def test_task_crud_and_confirmation_on_delete(client):
    sid = new_session(client)
    r = client.post("/tasks", json={"title": "Enviar relatório", "due": "amanhã às 9h", "priority": "alta"}, headers=H(sid))
    assert r.status_code == 201 and r.json()["seq"] == 1
    assert client.patch("/tasks/1", json={"priority": "baixa"}, headers=H(sid)).json()["priority"] == "baixa"
    assert client.post("/tasks/1/complete", headers=H(sid)).json()["status"] == "concluida"
    d = client.delete("/tasks/1", headers=H(sid))
    assert d.status_code == 428 and d.json()["error"] == "confirmation_required"
    assert client.delete("/tasks/1?confirm=true", headers=H(sid)).status_code == 200
    assert client.get("/tasks?status=todas", headers=H(sid)).json()["tasks"] == []


def test_validation_and_domain_errors_have_stable_codes(client):
    sid = new_session(client)
    assert client.post("/tasks", json={"title": "x", "priority": "x"}, headers=H(sid)).status_code == 422
    assert client.post("/tasks", json={"title": "x", "hack": 1}, headers=H(sid)).status_code == 422
    assert client.post("/reminders", json={"text": "x", "when": "ontem"}, headers=H(sid)).json()["error"] == "invalid_date"
    assert client.post("/tasks/9/complete", headers=H(sid)).status_code == 404


def test_sessions_are_isolated(client):
    a, b = new_session(client), new_session(client)
    client.post("/tasks", json={"title": "só do A"}, headers=H(a))
    assert client.get("/tasks", headers=H(b)).json()["tasks"] == []
    assert client.post("/tasks/1/complete", headers=H(b)).status_code == 404


def test_reminder_delivery_is_explicit(client):
    sid = new_session(client)
    client.post("/reminders", json={"text": "Ligar para Ana", "when": "daqui a 1 hora"}, headers=H(sid))
    assert client.get("/notifications/due", headers=H(sid)).json()["due"] == []
    client.clock.advance(hours=2)
    assert len(client.get("/notifications/due", headers=H(sid)).json()["due"]) == 1
    assert len(client.get("/notifications/due", headers=H(sid)).json()["due"]) == 1  # consultar não notifica
    assert client.post("/notifications/1/ack", headers=H(sid)).json()["state"] == "notificado"
    assert client.get("/notifications/due", headers=H(sid)).json()["due"] == []


def test_chat_demo_flow_with_pending_action(client):
    sid = new_session(client)
    client.post("/chat", json={"message": "Preciso comprar leite"}, headers=H(sid))
    r = client.post("/chat", json={"message": "Apague a tarefa comprar leite"}, headers=H(sid)).json()
    assert r["mode"] == "demo" and r["pending_action"]
    out = client.post(f"/actions/{r['pending_action']['token']}/confirm", headers=H(sid)).json()
    assert "excluída" in out["reply"]
    other = new_session(client)
    again = client.post(f"/actions/{r['pending_action']['token']}/confirm", headers=H(other)).json()
    assert again["error"] == "not_found"


def test_rag_endpoint_returns_sources_and_abstains(client):
    ok = client.post("/rag/search", json={"query": "Quantos dias de férias?"}).json()
    assert ok["sufficient"] and ok["passages"][0]["source"].startswith("politica_ferias.md")
    no = client.post("/rag/search", json={"query": "preço do bitcoin"}).json()
    assert no["sufficient"] is False and no["passages"] == []


def test_timezone_is_configurable_per_session(client):
    sid = new_session(client)
    assert client.put("/session/timezone", json={"timezone": "Nope/Zone"}, headers=H(sid)).status_code == 422
    assert client.put("/session/timezone", json={"timezone": "UTC"}, headers=H(sid)).status_code == 200
    t = client.post("/tasks", json={"title": "x", "due": "amanhã às 9h"}, headers=H(sid)).json()
    assert t["due_at"] == "2026-11-05T09:00:00Z"  # 09h em UTC, não em Brasília
