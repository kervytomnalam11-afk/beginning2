"""
word_bank.py - Word lists organized by difficulty tier for Spelling Sprint League.
Provides word selection based on player rank and game mode.
"""

import random
from typing import List, Dict

# ---------------------------------------------------------------------------
# Word lists by difficulty tier
# ---------------------------------------------------------------------------

WORDS: Dict[str, List[str]] = {
    "bronze": [
        "cat", "dog", "run", "jump", "play", "book", "tree", "fish", "bird", "cake",
        "ball", "milk", "rain", "ship", "star", "moon", "frog", "hand", "nose", "foot",
        "blue", "gold", "fast", "slow", "talk", "walk", "swim", "sing", "help", "make",
        "open", "read", "feel", "find", "grow", "keep", "hold", "move", "push", "pull",
        "very", "just", "also", "much", "more", "some", "last", "long", "high", "left",
    ],
    "silver": [
        "apple", "bread", "chair", "dance", "earth", "flame", "grape", "heart", "light",
        "magic", "night", "ocean", "place", "queen", "river", "stone", "table", "under",
        "voice", "water", "young", "zebra", "cloud", "dream", "eagle", "field", "ghost",
        "house", "input", "jewel", "knife", "lemon", "money", "nerve", "order", "paint",
        "quiet", "range", "sleep", "tiger", "union", "value", "whale", "xenon", "yacht",
        "angle", "basic", "clock", "depth", "event", "focus", "globe", "honor", "image",
    ],
    "gold": [
        "abstract", "balance", "captain", "diamond", "eclipse", "fantasy", "gallery",
        "horizon", "inspire", "journey", "kingdom", "lantern", "machine", "network",
        "opinion", "passion", "quality", "revenue", "science", "thought", "thunder",
        "unusual", "village", "warrior", "awesome", "bicycle", "charter", "digital",
        "element", "freedom", "gravity", "harvest", "library", "mineral", "mystery",
        "natural", "orbital", "perform", "quantum", "require", "session", "texture",
        "uniform", "venture", "weather", "examine", "fiction", "genuine", "husband",
    ],
    "platinum": [
        "accomplish", "beautiful", "celebrate", "different", "elaborate", "framework",
        "guarantee", "highlight", "implement", "knowledge", "landscape", "milestone",
        "narrative", "objective", "principle", "qualified", "represent", "situation",
        "technique", "universal", "vaccinate", "waterfall", "xylophone", "yesterday",
        "ambitious", "broadcast", "calculate", "determine", "encourage", "fortunate",
        "genuinely", "honorable", "important", "judgement", "kilometer", "legendary",
        "magnitude", "negotiate", "ownership", "physician", "quotation", "recommend",
        "strategic", "telephone", "undermine", "variation", "workpiece", "youngster",
    ],
    "diamond": [
        "accomplishment", "approximately", "breakthrough", "communication", "demonstrate",
        "establishment", "fundamentally", "gubernatorial", "hallucination", "independently",
        "juxtaposition", "knowledgeable", "liberalization", "magnification", "nevertheless",
        "opportunities", "predominantly", "questionnaire", "representative", "significantly",
        "transformation", "understandably", "vulnerabilities", "worthwhileness",
        "acknowledgment", "biodegradable", "circumspection", "disproportionate",
        "electromagnetic", "fragmentation", "geographically", "heterogeneous",
        "immunosuppressant", "juxtaposition", "kaleidoscope", "lamentation",
        "metamorphosis", "naturalization", "overwhelmingly", "parallelogram",
        "quintessential", "retrospectively", "sophisticated", "thermodynamics",
    ],
}

# All words combined for quick lookup
ALL_WORDS: List[str] = [w for tier in WORDS.values() for w in tier]


class WordBank:
    """Manages word selection and difficulty scaling for game sessions."""

    TIER_ORDER = ["bronze", "silver", "gold", "platinum", "diamond"]

    def __init__(self) -> None:
        self._used_words: List[str] = []

    def get_word(self, tier: str = "bronze", avoid_recent: int = 20) -> str:
        """
        Return a random word from the given tier.

        :param tier: Difficulty tier name.
        :param avoid_recent: Avoid the last N words to prevent repetition.
        :return: A word string.
        """
        tier = tier.lower()
        pool = WORDS.get(tier, WORDS["bronze"])
        # Include words from lower tiers for variety at higher tiers
        if tier in self.TIER_ORDER:
            idx = self.TIER_ORDER.index(tier)
            combined: List[str] = []
            for t in self.TIER_ORDER[: idx + 1]:
                combined.extend(WORDS[t])
        else:
            combined = pool

        # Filter recently used
        recent = self._used_words[-avoid_recent:] if len(self._used_words) >= avoid_recent else self._used_words
        candidates = [w for w in combined if w not in recent]
        if not candidates:
            candidates = combined  # Reset if all used

        word = random.choice(candidates)
        self._used_words.append(word)
        return word

    def get_word_list(self, tier: str = "bronze", count: int = 60) -> List[str]:
        """
        Generate a pre-shuffled list of words for a timed session.

        :param tier: Difficulty tier.
        :param count: Number of words to generate.
        :return: List of words.
        """
        self._used_words.clear()
        words = []
        for _ in range(count):
            words.append(self.get_word(tier))
        return words

    def get_tier_for_wpm(self, wpm: float) -> str:
        """Map WPM to appropriate word difficulty tier."""
        if wpm < 21:
            return "bronze"
        elif wpm < 36:
            return "silver"
        elif wpm < 51:
            return "gold"
        elif wpm < 71:
            return "platinum"
        return "diamond"

    def reset(self) -> None:
        """Clear used-word history."""
        self._used_words.clear()
