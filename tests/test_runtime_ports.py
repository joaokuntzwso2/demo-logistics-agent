from logistics_common.runtime import chat_agent_port, custom_api_port


def test_chat_agent_port_is_fixed_even_if_platform_sets_port(monkeypatch):
    monkeypatch.setenv("PORT", "8080")
    monkeypatch.setenv("CHAT_PORT", "9999")
    assert chat_agent_port() == 8000


def test_custom_api_defaults_to_8080(monkeypatch):
    monkeypatch.delenv("PORT", raising=False)
    assert custom_api_port() == 8080


def test_custom_api_honors_agent_manager_port(monkeypatch):
    monkeypatch.setenv("PORT", "8010")
    assert custom_api_port() == 8010
