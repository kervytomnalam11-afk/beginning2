"""
accuracy_tracker.py - Real-time accuracy calculation, heatmap generation,
and tier classification for Spelling Sprint League.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class CharEvent:
    """Records a single character input event."""
    char: str
    timestamp: float          # seconds since epoch
    was_correct: bool
    was_backspace: bool = False
    position: int = 0         # position in target string


@dataclass
class WordAccuracy:
    """Accuracy data for a single word attempt."""
    word: str
    correct_chars: int = 0
    total_chars: int = 0
    backspaces: int = 0
    time_taken: float = 0.0
    completed: bool = False


@dataclass
class AccuracyReport:
    """Full accuracy report for a completed game session."""
    overall_pct: float = 0.0
    tier: str = "Poor"
    tier_label: str = "Poor"
    bonus_points: int = 0
    penalty_pct: float = 0.0
    correct_chars: int = 0
    total_chars: int = 0
    total_backspaces: int = 0
    word_accuracies: List[WordAccuracy] = field(default_factory=list)
    # heatmap: dict mapping character position → error count
    error_heatmap: Dict[int, int] = field(default_factory=dict)
    accuracy_history: List[Tuple[float, float]] = field(default_factory=list)
    # (timestamp, running_accuracy_pct)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TIER_THRESHOLDS = [
    (100.0, "Perfect",   100,  0.0,  "#FFD700"),   # gold
    (95.0,  "Excellent",  25,  0.0,  "#69F0AE"),   # light green
    (90.0,  "Good",       10,  0.0,  "#00C853"),   # dark green
    (80.0,  "Fair",        0, -5.0,  "#FF9800"),   # orange
    (0.0,   "Poor",        0, -10.0, "#FF5252"),   # red
]


# ---------------------------------------------------------------------------
# AccuracyTracker
# ---------------------------------------------------------------------------

class AccuracyTracker:
    """
    Tracks accuracy at the character level throughout a game session.
    Provides live accuracy percentage, tier classification,
    heatmap data, and bonus/penalty calculation.
    """

    def __init__(self) -> None:
        self.reset()

    # ── Session management ─────────────────────────────────────────────────

    def reset(self) -> None:
        """Reset all tracking state for a new session."""
        self._events: List[CharEvent] = []
        self._word_accuracies: List[WordAccuracy] = []
        self._current_word: Optional[WordAccuracy] = None
        self._session_start: float = time.time()
        self._last_snapshot_time: float = 0.0
        self._snapshot_interval: float = 1.0   # seconds
        self._accuracy_history: List[Tuple[float, float]] = []
        self._correct_chars: int = 0
        self._total_chars: int = 0
        self._backspaces: int = 0

    def start_word(self, word: str) -> None:
        """Begin tracking a new target word."""
        if self._current_word and not self._current_word.completed:
            # Abandon previous word
            self._word_accuracies.append(self._current_word)
        self._current_word = WordAccuracy(word=word)
        self._word_start_time: float = time.time()

    # ── Per-keystroke recording ────────────────────────────────────────────

    def record_char(self, char: str, is_correct: bool, position: int = 0) -> None:
        """
        Record a typed character.

        :param char: The character typed.
        :param is_correct: Whether it matched the target.
        :param position: Position index in the target string.
        """
        now = time.time()
        event = CharEvent(
            char=char,
            timestamp=now,
            was_correct=is_correct,
            position=position,
        )
        self._events.append(event)
        self._total_chars += 1
        if is_correct:
            self._correct_chars += 1
        if self._current_word:
            self._current_word.total_chars += 1
            if is_correct:
                self._current_word.correct_chars += 1

        # Snapshot accuracy for history graph
        if now - self._last_snapshot_time >= self._snapshot_interval:
            self._accuracy_history.append((now, self.current_accuracy()))
            self._last_snapshot_time = now

    def record_backspace(self, position: int = 0) -> None:
        """Record a backspace (counts against accuracy)."""
        now = time.time()
        event = CharEvent(
            char="⌫",
            timestamp=now,
            was_correct=False,
            was_backspace=True,
            position=position,
        )
        self._events.append(event)
        self._backspaces += 1
        if self._current_word:
            self._current_word.backspaces += 1

    def complete_word(self) -> WordAccuracy:
        """Finalize the current word and return its accuracy stats."""
        if not self._current_word:
            return WordAccuracy(word="")
        wa = self._current_word
        wa.time_taken = time.time() - self._word_start_time
        wa.completed = True
        self._word_accuracies.append(wa)
        self._current_word = None
        return wa

    # ── Live accuracy ──────────────────────────────────────────────────────

    def current_accuracy(self) -> float:
        """
        Return running accuracy percentage (0–100).
        Formula: (correct - backspaces) / total × 100, clamped to [0, 100].
        """
        if self._total_chars == 0:
            return 100.0
        score = max(0, self._correct_chars - self._backspaces)
        pct = (score / self._total_chars) * 100.0
        return min(100.0, max(0.0, pct))

    def get_tier(self, accuracy: Optional[float] = None) -> Tuple[str, str, int, float, str]:
        """
        Classify accuracy into a tier.

        :param accuracy: Override accuracy value; defaults to current_accuracy().
        :return: (tier_name, label, bonus_points, penalty_pct, color_hex)
        """
        pct = accuracy if accuracy is not None else self.current_accuracy()
        for threshold, label, bonus, penalty, color in TIER_THRESHOLDS:
            if pct >= threshold:
                return (label.lower().replace(" ", "_"), label, bonus, penalty, color)
        return ("poor", "Poor", 0, -10.0, "#FF5252")

    # ── Heatmap ───────────────────────────────────────────────────────────

    def build_error_heatmap(self) -> Dict[int, int]:
        """
        Build a character-position → error-count heatmap.

        :return: Dict mapping position index to number of errors at that position.
        """
        heatmap: Dict[int, int] = {}
        for event in self._events:
            if not event.was_correct and not event.was_backspace:
                heatmap[event.position] = heatmap.get(event.position, 0) + 1
        return heatmap

    # ── Full session report ────────────────────────────────────────────────

    def generate_report(self) -> AccuracyReport:
        """Generate a complete accuracy report for the finished session."""
        accuracy = self.current_accuracy()
        tier_name, tier_label, bonus, penalty, _ = self.get_tier(accuracy)
        heatmap = self.build_error_heatmap()

        report = AccuracyReport(
            overall_pct=round(accuracy, 1),
            tier=tier_name,
            tier_label=tier_label,
            bonus_points=bonus,
            penalty_pct=penalty,
            correct_chars=self._correct_chars,
            total_chars=self._total_chars,
            total_backspaces=self._backspaces,
            word_accuracies=list(self._word_accuracies),
            error_heatmap=heatmap,
            accuracy_history=list(self._accuracy_history),
        )
        return report

    # ── Serialization ──────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialize current state for ghost recording."""
        return {
            "correct_chars": self._correct_chars,
            "total_chars": self._total_chars,
            "backspaces": self._backspaces,
            "accuracy_pct": self.current_accuracy(),
            "heatmap": self.build_error_heatmap(),
            "accuracy_history": [
                {"t": t, "pct": p} for t, p in self._accuracy_history
            ],
        }

    @staticmethod
    def accuracy_color(pct: float) -> str:
        """Return the hex color string for a given accuracy percentage."""
        for threshold, _, _, _, color in TIER_THRESHOLDS:
            if pct >= threshold:
                return color
        return "#FF5252"

    @staticmethod
    def format_accuracy(pct: float) -> str:
        """Human-readable accuracy string with tier label."""
        for threshold, label, _, _, _ in TIER_THRESHOLDS:
            if pct >= threshold:
                return f"{pct:.1f}% ({label})"
        return f"{pct:.1f}% (Poor)"
