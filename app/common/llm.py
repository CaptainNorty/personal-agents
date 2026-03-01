from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from app.config import settings

llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    anthropic_api_key=settings.anthropic_api_key,
)


async def ask_claude(prompt: str, system: str | None = None) -> str:
    """Send a prompt to Claude and return the response text."""
    messages: list = []
    if system:
        messages.append(SystemMessage(content=system))
    messages.append(HumanMessage(content=prompt))
    response = await llm.ainvoke(messages)
    return str(response.content)
