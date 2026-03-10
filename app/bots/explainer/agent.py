from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

from app.common.llm import llm

SYSTEM_PROMPT = """\
You are a masterful explainer. When given a topic, write a clear, concise explanation \
suitable for being read aloud as a voice memo. Keep it conversational and under ~2 minutes \
when spoken. Avoid markdown formatting, bullet points, or special characters — write in \
natural prose that sounds good when read aloud.\
"""

checkpointer = InMemorySaver()

explainer_agent = create_agent(
    model=llm,
    tools=[],
    system_prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,
)
