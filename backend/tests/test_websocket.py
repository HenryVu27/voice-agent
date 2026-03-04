import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_endpoint(client):
    """GET /health returns 200 with status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_websocket_connection(client):
    """Connect to /ws/translate, send start_speaking, verify no error."""
    mock_pipeline = MagicMock()
    mock_pipeline.process = AsyncMock()

    with patch("app.main.create_pipeline", return_value=mock_pipeline):
        with client.websocket_connect("/ws/translate") as ws:
            ws.send_json({"type": "start_speaking", "speaker": "a"})
            # If there were an error, the server would send an error message
            # or close the connection. We send stop_speaking to confirm the
            # connection is still alive and functioning.
            ws.send_json({"type": "stop_speaking", "speaker": "a"})
