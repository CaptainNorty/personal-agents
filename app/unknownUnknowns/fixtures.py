"""
Backend-side placeholder topic content. Each entry carries the cold prompt, the
curriculum bullets (the anchor the day-of briefing generator will hit), and the
final-challenge prompt.

Mirrors the frontend's `src/data/fakeTopics.ts` for now — both go away once the
end-of-session LLM generation pipeline is wired up (runs when the user
finishes the day, prepping content for the next day).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TopicFixture:
    category: str
    cold_prompt: str
    final_prompt: str
    curriculum_bullets: list[str]


FAKE_TOPICS: list[TopicFixture] = [
    TopicFixture(
        category="technical",
        cold_prompt="Why is the sky blue?",
        final_prompt="Why does the sun look red at sunset?",
        curriculum_bullets=[
            "Air scatters short wavelengths more than long ones — Rayleigh scattering.",
            "Rayleigh's law: scattering intensity scales as 1/λ⁴; blue (~470nm) scatters ~10× more than red (~700nm).",
            "Sky looks blue not violet because the sun emits less violet, our eyes are less sensitive to it, and some is absorbed in the upper atmosphere.",
            "At sunset, the longer atmospheric path scatters out blue, leaving reds and oranges to dominate.",
        ],
    ),
    TopicFixture(
        category="technical",
        cold_prompt="What is entropy?",
        final_prompt=(
            "If entropy always increases, how did the universe start in such a "
            "low-entropy state?"
        ),
        curriculum_bullets=[
            "Entropy = count of microscopic configurations consistent with a given macroscopic state.",
            "Second law is statistical, not fundamental: high-entropy states are overwhelmingly more numerous.",
            "The arrow of time is widely attributed to this statistical asymmetry.",
            "'Entropy = disorder' is loose — more precisely it's uncertainty about microscopic state given macroscopic description.",
        ],
    ),
    TopicFixture(
        category="cultural",
        cold_prompt="What was the Treaty of Westphalia?",
        final_prompt=(
            "Why did later historians call Westphalia the birth of state "
            "sovereignty if the treaties did not say so?"
        ),
        curriculum_bullets=[
            "1648 — actually two treaties (Münster and Osnabrück) ending the Thirty Years' War.",
            "Extended cuius regio, eius religio (rulers, not popes, set religion) across the empire's polities.",
            "Sovereignty principle (territorial authority, non-intervention) is the cleaner retconned claim.",
            "Westphalian sovereignty as a coherent doctrine was largely retrofitted in the 19th–20th centuries.",
        ],
    ),
]
