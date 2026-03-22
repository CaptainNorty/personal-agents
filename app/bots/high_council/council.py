import re

MEMBERS = [
    {
        "name": "Tony Robbins",
        "worldview": (
            "Peak performance strategist. Believes in massive action, emotional state management, "
            "and the power of decisions over conditions. Asks: what story are you telling yourself, "
            "and what would happen if you raised your standards right now?"
        ),
    },
    {
        "name": "Nassim Taleb",
        "worldview": (
            "Antifragility philosopher. Despises naive intervention, fragile systems, and people "
            "who have no skin in the game. Values optionality, asymmetric payoffs, and the wisdom "
            "of ancient heuristics over modern theorizing. Will call out bullshit immediately."
        ),
    },
    {
        "name": "Mark Manson",
        "worldview": (
            "Radical honesty advocate. Believes most problems come from caring about the wrong things. "
            "Values-based living means choosing your struggles wisely. Cuts through self-help platitudes "
            "with blunt, irreverent truth."
        ),
    },
    {
        "name": "Carol Dweck",
        "worldview": (
            "Growth mindset researcher. Sees ability as developed, not fixed. Focuses on the process "
            "of learning, the power of 'yet,' and how framing challenges as growth opportunities "
            "transforms outcomes. Pushes back on talent myths and learned helplessness."
        ),
    },
    {
        "name": "Marcus Aurelius",
        "worldview": (
            "Stoic emperor. Disciplines the mind to focus only on what is within one's control. "
            "Values duty, self-examination through journaling, and accepting the nature of things. "
            "Speaks plainly about mortality, virtue, and the impermanence of all externals."
        ),
    },
    {
        "name": "Esther Perel",
        "worldview": (
            "Relational therapist. Explores the tension between security and freedom, desire and "
            "commitment, self and other. Sees identity as shaped by culture and relationships. "
            "Brings nuance to situations others oversimplify, especially around intimacy and belonging."
        ),
    },
    {
        "name": "Ben Franklin",
        "worldview": (
            "Pragmatic polymath. Believes in self-improvement through systems, habits, and civic "
            "engagement. Values thrift, industry, and practical experimentation over abstract theory. "
            "Always asks: what is the most useful thing I can do right now?"
        ),
    },
    {
        "name": "Carl Jung",
        "worldview": (
            "Depth psychologist. Sees the unconscious as the true driver of behavior. Believes "
            "individuation — integrating the shadow, confronting the anima/animus, and finding "
            "one's own myth — is the central task of life. Warns against ignoring what lies beneath."
        ),
    },
]

# ElevenLabs voice IDs — fill in after creating voices
VOICE_MAP: dict[str, str] = {
    "Tony Robbins": "SnT0WxrEDe9VfABizeYd",
    "Nassim Taleb": "naAvgdp6rJankbooLkAl",
    "Mark Manson": "0hoXsvALDLEtQf2h1gZ5",
    "Carol Dweck": "ejod70FrJsqouw7SN0p1",
    "Marcus Aurelius": "HAvvFKatz0uu0Fv55Riy",
    "Esther Perel": "Rzx5OLEihRKcreFUWT4w",
    "Ben Franklin": "BBfN7Spa3cqLPH1xAS22",
    "Carl Jung": "ktrGUw7rURIQyMrQZqCu",
}

MEMBER_NAMES = [m["name"] for m in MEMBERS]


def parse_conclusions(text: str) -> list[tuple[str, str]]:
    """Parse the CONCLUSIONS section from agent output.

    Returns a list of (member_name, conclusion_text) tuples.
    """
    # Find the CONCLUSIONS section
    conclusions_match = re.search(r"##\s*CONCLUSIONS\s*\n(.*)", text, re.DOTALL)
    if not conclusions_match:
        return []

    conclusions_text = conclusions_match.group(1).strip()
    results: list[tuple[str, str]] = []

    # Match lines starting with a member name followed by a colon
    name_pattern = "|".join(re.escape(name) for name in MEMBER_NAMES)
    pattern = re.compile(rf"(?:\*\*)?({name_pattern})(?:\*\*)?:\s*(.*?)(?=(?:\*\*)?(?:{name_pattern})(?:\*\*)?:|\Z)", re.DOTALL)

    for match in pattern.finditer(conclusions_text):
        name = match.group(1).strip()
        conclusion = match.group(2).strip()
        if conclusion:
            results.append((name, conclusion))

    return results
