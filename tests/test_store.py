from mock_core.store import LogisticsStore


def test_primary_shipment_starts_with_projected_sla_breach():
    store = LogisticsStore()
    sla = store.sla("BRX-784512")
    assert sla is not None
    assert sla["sla_at_risk"] is True
    assert sla["projected_delay_minutes"] == 930
    assert sla["severity"] == "critical"


def test_disruption_priority_order_is_realistic():
    store = LogisticsStore()
    impact = store.impacted_ranked("DISR-GRU-0908")
    assert impact is not None
    assert [row["tracking_number"] for row in impact] == [
        "BRX-784512",
        "BRX-784533",
        "BRX-784540",
    ]
    assert impact[0]["priority"] == "P1"
    assert impact[1]["priority"] == "P2"
    assert impact[2]["priority"] == "P4"


def test_approved_recovery_updates_shared_eta_and_tracking_event():
    store = LogisticsStore()
    before = store.get_shipment("BRX-784512")
    result = store.execute_recovery(
        "BRX-784512",
        "REC-ATL-VCP",
        approved_by="Demo Operations Manager",
        approval_reference="APPROVED-DEMO-001",
    )
    after = store.get_shipment("BRX-784512")
    assert result is not None
    assert before["estimated_delivery"] == "2026-09-09T09:30:00-03:00"
    assert after["estimated_delivery"] == "2026-09-08T21:40:00-03:00"
    assert after["recovery_status"] == "executed"
    events = store.tracking_events("BRX-784512")
    assert events[-1]["code"] == "RECOVERY_BOOKED"
    assert store.sla("BRX-784512")["projected_delay_minutes"] == 220


def test_case_creation_is_idempotent_for_open_case():
    store = LogisticsStore()
    first = store.create_case("BRX-784512", "Projected delay")
    second = store.create_case("BRX-784512", "Projected delay again")
    assert first["case_id"] == second["case_id"]


def test_reset_restores_original_eta_and_removes_actions():
    store = LogisticsStore()
    store.execute_recovery(
        "BRX-784512",
        "REC-ATL-VCP",
        approved_by="Demo Operations Manager",
        approval_reference="APPROVED-DEMO-001",
    )
    store.reset()
    assert store.get_shipment("BRX-784512")["estimated_delivery"] == "2026-09-09T09:30:00-03:00"
    assert store.state_summary()["recovery_actions"] == []
