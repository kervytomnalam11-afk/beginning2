"""
sentence_bank.py - Sentence/passage database for Spelling Sprint League.
Provides categorized sentences of varying difficulty for Sentence Race mode.
"""

import random
from typing import List, Dict, Optional

# ---------------------------------------------------------------------------
# Sentence data — each entry is a dict with fields used by SentenceBank
# ---------------------------------------------------------------------------

SENTENCES: List[Dict] = [
    # ── Famous Quotes ──────────────────────────────────────────────────────
    {"id": "q001", "text": "Be yourself; everyone else is already taken.",
     "difficulty": "short", "category": "quotes", "word_count": 8, "char_count": 43},
    {"id": "q002", "text": "The only way to do great work is to love what you do.",
     "difficulty": "medium", "category": "quotes", "word_count": 12, "char_count": 53},
    {"id": "q003", "text": "In the middle of every difficulty lies opportunity.",
     "difficulty": "medium", "category": "quotes", "word_count": 9, "char_count": 51},
    {"id": "q004", "text": "Imagination is more important than knowledge.",
     "difficulty": "short", "category": "quotes", "word_count": 7, "char_count": 45},
    {"id": "q005", "text": "The journey of a thousand miles begins with a single step.",
     "difficulty": "medium", "category": "quotes", "word_count": 12, "char_count": 57},
    {"id": "q006", "text": "You must be the change you wish to see in the world.",
     "difficulty": "medium", "category": "quotes", "word_count": 12, "char_count": 52},
    {"id": "q007", "text": "Success is not final; failure is not fatal: it is the courage to continue that counts.",
     "difficulty": "long", "category": "quotes", "word_count": 17, "char_count": 87},
    {"id": "q008", "text": "Life is what happens when you are busy making other plans.",
     "difficulty": "medium", "category": "quotes", "word_count": 12, "char_count": 57},
    {"id": "q009", "text": "The future belongs to those who believe in the beauty of their dreams.",
     "difficulty": "long", "category": "quotes", "word_count": 14, "char_count": 70},
    {"id": "q010", "text": "Spread love everywhere you go.",
     "difficulty": "short", "category": "quotes", "word_count": 6, "char_count": 30},

    # ── Science Facts ──────────────────────────────────────────────────────
    {"id": "s001", "text": "Light travels at three hundred thousand kilometers per second.",
     "difficulty": "medium", "category": "science", "word_count": 10, "char_count": 60},
    {"id": "s002", "text": "The human body contains approximately thirty-seven trillion cells.",
     "difficulty": "medium", "category": "science", "word_count": 9, "char_count": 62},
    {"id": "s003", "text": "Water boils at one hundred degrees Celsius at sea level.",
     "difficulty": "medium", "category": "science", "word_count": 11, "char_count": 55},
    {"id": "s004", "text": "DNA is the molecule that carries genetic information in living organisms.",
     "difficulty": "long", "category": "science", "word_count": 12, "char_count": 72},
    {"id": "s005", "text": "Gravity pulls objects toward Earth at nine point eight meters per second squared.",
     "difficulty": "long", "category": "science", "word_count": 14, "char_count": 79},
    {"id": "s006", "text": "The Earth orbits the Sun once every three hundred sixty-five days.",
     "difficulty": "medium", "category": "science", "word_count": 12, "char_count": 64},
    {"id": "s007", "text": "Sound travels faster through water than through air.",
     "difficulty": "short", "category": "science", "word_count": 9, "char_count": 51},
    {"id": "s008", "text": "Atoms are mostly empty space with a dense nucleus at the center.",
     "difficulty": "medium", "category": "science", "word_count": 13, "char_count": 63},

    # ── Historical Facts ───────────────────────────────────────────────────
    {"id": "h001", "text": "The Great Wall of China stretches over twenty thousand kilometers.",
     "difficulty": "medium", "category": "history", "word_count": 11, "char_count": 63},
    {"id": "h002", "text": "World War Two ended in nineteen forty-five after six years of conflict.",
     "difficulty": "long", "category": "history", "word_count": 13, "char_count": 70},
    {"id": "h003", "text": "The ancient Egyptians built the pyramids as royal tombs.",
     "difficulty": "short", "category": "history", "word_count": 10, "char_count": 54},
    {"id": "h004", "text": "Neil Armstrong became the first human to walk on the Moon in nineteen sixty-nine.",
     "difficulty": "long", "category": "history", "word_count": 15, "char_count": 80},
    {"id": "h005", "text": "The printing press was invented by Johannes Gutenberg around fourteen fifty.",
     "difficulty": "long", "category": "history", "word_count": 12, "char_count": 73},
    {"id": "h006", "text": "Julius Caesar was assassinated on the Ides of March.",
     "difficulty": "short", "category": "history", "word_count": 10, "char_count": 51},

    # ── Literature Excerpts ────────────────────────────────────────────────
    {"id": "l001", "text": "It was the best of times it was the worst of times.",
     "difficulty": "short", "category": "literature", "word_count": 13, "char_count": 52},
    {"id": "l002", "text": "All that glitters is not gold often have you heard that told.",
     "difficulty": "medium", "category": "literature", "word_count": 13, "char_count": 62},
    {"id": "l003", "text": "To be or not to be that is the question.",
     "difficulty": "short", "category": "literature", "word_count": 10, "char_count": 41},
    {"id": "l004", "text": "It is a truth universally acknowledged that a single man in possession of a good fortune.",
     "difficulty": "long", "category": "literature", "word_count": 16, "char_count": 89},
    {"id": "l005", "text": "Call me Ishmael and some years ago I went to sea.",
     "difficulty": "short", "category": "literature", "word_count": 12, "char_count": 52},
    {"id": "l006", "text": "Not all those who wander are lost in the wilderness of the world.",
     "difficulty": "medium", "category": "literature", "word_count": 14, "char_count": 65},

    # ── Tongue Twisters ────────────────────────────────────────────────────
    {"id": "t001", "text": "She sells seashells by the seashore.",
     "difficulty": "short", "category": "tongue_twister", "word_count": 6, "char_count": 36},
    {"id": "t002", "text": "Peter Piper picked a peck of pickled peppers.",
     "difficulty": "short", "category": "tongue_twister", "word_count": 9, "char_count": 45},
    {"id": "t003", "text": "How much wood would a woodchuck chuck if a woodchuck could chuck wood.",
     "difficulty": "medium", "category": "tongue_twister", "word_count": 14, "char_count": 69},
    {"id": "t004", "text": "Betty Botter bought some butter but the butter Betty bought was bitter.",
     "difficulty": "medium", "category": "tongue_twister", "word_count": 13, "char_count": 70},
    {"id": "t005", "text": "Red lorry yellow lorry red lorry yellow lorry again and again.",
     "difficulty": "medium", "category": "tongue_twister", "word_count": 11, "char_count": 61},

    # ── Educational Facts ──────────────────────────────────────────────────
    {"id": "e001", "text": "Reading improves vocabulary and strengthens the brain.",
     "difficulty": "short", "category": "education", "word_count": 8, "char_count": 53},
    {"id": "e002", "text": "Regular practice is the key to becoming a better speller.",
     "difficulty": "short", "category": "education", "word_count": 11, "char_count": 56},
    {"id": "e003", "text": "Typing speed is measured in words per minute using standardized five-letter words.",
     "difficulty": "long", "category": "education", "word_count": 13, "char_count": 80},
    {"id": "e004", "text": "Spelling accuracy improves when you practice writing words by hand.",
     "difficulty": "medium", "category": "education", "word_count": 11, "char_count": 65},
    {"id": "e005", "text": "The alphabet has twenty-six letters that form the foundation of English.",
     "difficulty": "medium", "category": "education", "word_count": 12, "char_count": 70},
]

# Difficulty → required tier mapping
DIFFICULTY_TIERS: Dict[str, List[str]] = {
    "short": ["bronze", "silver"],
    "medium": ["gold"],
    "long": ["platinum", "diamond"],
}

# Reverse mapping: tier → allowed difficulties
TIER_DIFFICULTY_MAP: Dict[str, List[str]] = {
    "bronze": ["short"],
    "silver": ["short"],
    "gold": ["short", "medium"],
    "platinum": ["medium", "long"],
    "diamond": ["medium", "long"],
}


class SentenceBank:
    """Manages sentence selection for Sentence Race mode."""

    def __init__(self) -> None:
        self._used_ids: List[str] = []

    def get_sentence(
        self,
        tier: str = "gold",
        category: Optional[str] = None,
    ) -> Dict:
        """
        Return a sentence appropriate for the given tier.

        :param tier: Player difficulty tier.
        :param category: Optional filter by category name.
        :return: Sentence dict.
        """
        allowed_diffs = TIER_DIFFICULTY_MAP.get(tier, ["short", "medium"])
        candidates = [
            s for s in SENTENCES
            if s["difficulty"] in allowed_diffs
            and s["id"] not in self._used_ids[-10:]
        ]
        if category:
            filtered = [s for s in candidates if s["category"] == category]
            if filtered:
                candidates = filtered

        if not candidates:
            candidates = SENTENCES  # fallback

        chosen = random.choice(candidates)
        self._used_ids.append(chosen["id"])
        return chosen

    def get_sentence_list(
        self, tier: str = "gold", count: int = 10, category: Optional[str] = None
    ) -> List[Dict]:
        """Return a list of sentences for a game session."""
        self._used_ids.clear()
        return [self.get_sentence(tier, category) for _ in range(count)]

    def get_by_id(self, sentence_id: str) -> Optional[Dict]:
        """Fetch a sentence by its unique ID."""
        for s in SENTENCES:
            if s["id"] == sentence_id:
                return s
        return None

    @staticmethod
    def get_categories() -> List[str]:
        """Return all available categories."""
        return list({s["category"] for s in SENTENCES})

    @staticmethod
    def get_difficulties() -> List[str]:
        return ["short", "medium", "long"]

    def reset(self) -> None:
        self._used_ids.clear()
