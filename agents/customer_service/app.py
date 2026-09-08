from logistics_common.chat_app import create_chat_app

from .prompt import SYSTEM_PROMPT
from .tools import LANGCHAIN_TOOLS

app = create_chat_app(
    name="TransNova Customer Experience Agent",
    slug="transnova-customer-experience",
    description="Customer/order/tracking assistant for the TransNova logistics demo.",
    system_prompt=SYSTEM_PROMPT,
    tools=LANGCHAIN_TOOLS,
)
