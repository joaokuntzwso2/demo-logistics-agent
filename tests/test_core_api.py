from fastapi.testclient import TestClient

from mock_core.app import app
from mock_core.store import STORE

client = TestClient(app)


def setup_function():
    STORE.reset()


def test_health_and_scenario():
    assert client.get("/health").status_code == 200
    scenario = client.get("/demo/scenario").json()
    assert scenario["primary_disruption"] == "DISR-GRU-0908"
    assert scenario["showcase_tracking"] == "BRX-784512"


def test_tracking_and_sla_endpoints():
    shipment = client.get("/shipments/BRX-784512")
    assert shipment.status_code == 200
    assert shipment.json()["status"] == "exception"
    sla = client.get("/shipments/BRX-784512/sla").json()
    assert sla["projected_delay_minutes"] == 930


def test_recovery_api_mutates_in_memory_database():
    response = client.post(
        "/shipments/BRX-784512/recovery",
        json={
            "option_id": "REC-ATL-VCP",
            "approved_by": "Demo Manager",
            "approval_reference": "APPROVED-DEMO-001",
        },
    )
    assert response.status_code == 200
    current = client.get("/shipments/BRX-784512").json()
    assert current["estimated_delivery"] == "2026-09-08T21:40:00-03:00"
