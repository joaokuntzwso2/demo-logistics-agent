from demo_portal.client import PortalGateway
from demo_portal.config import ServiceTarget


def test_api_key_header_is_only_added_when_configured():
    no_key = ServiceTarget(name="No Key", url="http://example.test", api_key="", kind="chat-agent")
    with_key = ServiceTarget(name="With Key", url="http://example.test", api_key="secret", kind="chat-agent")

    assert "X-API-Key" not in PortalGateway._headers(no_key)
    assert PortalGateway._headers(with_key)["X-API-Key"] == "secret"
