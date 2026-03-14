from pathlib import Path

from langchain.agents import create_agent
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from loguru import logger

from app.common.llm import llm

LIFE_CONTEXT_PATH = Path(__file__).parent / "life_context.md"

SYSTEM_PROMPT = """\
You are a masterful explainer, Uncle Iroh. You are a master of finance, modern code solutions, \
and can explain complex topics such that anyone can understand them. \
When given a topic, write a clear, concise explanation \
suitable for being read aloud as a voice memo. Keep it conversational and under ~2 minutes \
when spoken. Avoid markdown formatting, bullet points, or special characters — write in \
natural prose that sounds good when read aloud.

IMPORTANT: Always call get_life_context at the start of every conversation to understand \
who you are speaking with. Use this context to tailor your explanations — reference things \
the user already knows, connect new concepts to their experience, and adjust depth accordingly.\
"""


@tool
async def get_life_context() -> str:
    """Fetch the markdown file containing context about the user's life,
    background, interests, and knowledge. Call this at the start of every
    conversation to personalize explanations."""
    try:
        content = LIFE_CONTEXT_PATH.read_text()
        logger.info("Loaded life context file")
        return content
    except FileNotFoundError:
        logger.warning("Life context file not found")
        return "No life context file found. Proceed without personalization."


checkpointer = InMemorySaver()

explainer_agent = create_agent(
    model=llm,
    tools=[get_life_context],
    system_prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,
)
