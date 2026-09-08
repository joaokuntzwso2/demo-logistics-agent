from fastapi.testclient import TestClient

from demo_portal.app import app
from mock_core.app import app as core_app


def test_portal_serves_professional_ui():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "TransNova Logistics AI Operations" in response.text
    assert "Mock Data Explorer" in response.text
    assert "Human approves execution" not in response.text  # rendered by JS, not static duplication


def test_core_catalog_exposes_mock_source_of_truth():
    client = TestClient(core_app)
    response = client.get("/demo/catalog")
    assert response.status_code == 200
    data = response.json()
    assert data["mocked"] is True
    assert data["scenario"]["showcase_tracking"] == "BRX-784512"
    assert "BRX-784512" in data["shipments"]
    assert "DISR-GRU-0908" in data["disruptions"]
    assert "REC-ATL-VCP" in [x["option_id"] for x in data["recovery_options"]["BRX-784512"]]
