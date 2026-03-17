"""
ghost_manager.py - Ghost recording, playback, file I/O, and QR code
encoding/decoding for Spelling Sprint League.
"""

import json
import os
import time
import base64
import gzip
import random
import string
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GHOST_DIR = os.path.join(
    os.path.expanduser("~"), "SpellingSprint", "Ghosts"
)
MAX_PERSONAL_GHOSTS = 10
GHOST_VERSION = "1.0"

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class KeystrokeEvent:
    """A single keystroke during a recorded ghost run."""
    t: float          # time offset in seconds since run start
    char: str         # character typed
    correct: bool     # whether the character was correct
    word_idx: int     # index of target word/sentence at this point


@dataclass
class GhostMeta:
    """Metadata for a ghost recording."""
    ghost_id: str
    name: str                    # player/device name
    date_recorded: str           # ISO date string
    wpm: float
    accuracy_pct: float
    score: int
    difficulty_tier: str
    game_mode: str               # "word" | "sentence"
    total_words: int
    total_chars: int
    duration_secs: float
    accuracy_tier: str           # "perfect" | "excellent" | "good" | "fair" | "poor"
    version: str = GHOST_VERSION


@dataclass
class GhostRecording:
    """Full ghost recording including keystrokes and words/sentences."""
    meta: GhostMeta
    word_list: List[str]                  # words or sentence IDs shown
    keystroke_events: List[KeystrokeEvent]
    error_positions: Dict[str, int]       # position → error count
    accuracy_heatmap: Dict[str, float]    # position → heat value 0-1
    word_completion_times: List[float]    # cumulative seconds per word


# ---------------------------------------------------------------------------
# Ghost playback helper
# ---------------------------------------------------------------------------

@dataclass
class GhostPlayback:
    """
    Thin wrapper used during live ghost racing to query ghost progress.
    Updated by GhostManager.tick() calls every frame.
    """
    recording: GhostRecording
    start_time: float = field(default_factory=time.time)
    _event_idx: int = 0
    current_word_idx: int = 0
    chars_typed: int = 0
    words_completed: int = 0
    elapsed: float = 0.0
    finished: bool = False

    def tick(self, now: float) -> None:
        """Advance ghost state to the current real-world timestamp."""
        self.elapsed = now - self.start_time
        events = self.recording.keystroke_events
        while (
            self._event_idx < len(events)
            and events[self._event_idx].t <= self.elapsed
        ):
            evt = events[self._event_idx]
            self.chars_typed += 1
            self.current_word_idx = evt.word_idx
            self._event_idx += 1

        # Update words_completed via completion times
        times = self.recording.word_completion_times
        self.words_completed = sum(1 for t in times if t <= self.elapsed)
        if self.words_completed >= len(self.recording.word_list):
            self.finished = True

    @property
    def progress_pct(self) -> float:
        """Return 0–100 progress through the session."""
        total = len(self.recording.word_list)
        if total == 0:
            return 100.0
        return min(100.0, (self.words_completed / total) * 100.0)

    @property
    def live_wpm(self) -> float:
        """Calculate ghost's live WPM at the current playback moment."""
        if self.elapsed < 1.0:
            return 0.0
        return (self.chars_typed / 5.0) / (self.elapsed / 60.0)


# ---------------------------------------------------------------------------
# GhostManager
# ---------------------------------------------------------------------------

class GhostManager:
    """
    Manages ghost recording, storage, playback, and import/export.
    """

    def __init__(self, ghost_dir: str = GHOST_DIR) -> None:
        self.ghost_dir = ghost_dir
        os.makedirs(ghost_dir, exist_ok=True)

        # Active recording state
        self._recording: bool = False
        self._record_start: float = 0.0
        self._events: List[KeystrokeEvent] = []
        self._word_list: List[str] = []
        self._word_completion_times: List[float] = []
        self._current_word_idx: int = 0
        self._error_positions: Dict[str, int] = {}
        self._device_name: str = "Player"
        self._game_mode: str = "word"
        self._tier: str = "bronze"

    # ── Recording ─────────────────────────────────────────────────────────

    def start_recording(
        self,
        word_list: List[str],
        device_name: str = "Player",
        game_mode: str = "word",
        tier: str = "bronze",
    ) -> None:
        """Begin a new ghost recording session."""
        self._recording = True
        self._record_start = time.time()
        self._events = []
        self._word_list = list(word_list)
        self._word_completion_times = []
        self._current_word_idx = 0
        self._error_positions = {}
        self._device_name = device_name
        self._game_mode = game_mode
        self._tier = tier

    def record_keystroke(self, char: str, correct: bool, position: int = 0) -> None:
        """Record a single keystroke during the active session."""
        if not self._recording:
            return
        t = time.time() - self._record_start
        self._events.append(
            KeystrokeEvent(t=t, char=char, correct=correct, word_idx=self._current_word_idx)
        )
        if not correct:
            key = str(position)
            self._error_positions[key] = self._error_positions.get(key, 0) + 1

    def complete_word(self, word_idx: int) -> None:
        """Mark a word/sentence as completed at the current timestamp."""
        if not self._recording:
            return
        self._current_word_idx = word_idx + 1
        self._word_completion_times.append(time.time() - self._record_start)

    def stop_recording(
        self,
        wpm: float,
        accuracy_pct: float,
        score: int,
        accuracy_tier: str,
        player_name: str = "",
    ) -> Optional[GhostRecording]:
        """
        Stop recording and build the GhostRecording object.
        Returns None if recording was not active.
        """
        if not self._recording:
            return None
        self._recording = False
        duration = time.time() - self._record_start

        ghost_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        from datetime import datetime
        date_str = datetime.now().strftime("%Y-%m-%d")

        # Build accuracy heatmap (normalise error counts to 0-1)
        max_errors = max(self._error_positions.values(), default=1)
        heatmap = {
            pos: count / max_errors
            for pos, count in self._error_positions.items()
        }

        total_chars = len(self._events)

        meta = GhostMeta(
            ghost_id=ghost_id,
            name=player_name or self._device_name,
            date_recorded=date_str,
            wpm=round(wpm, 1),
            accuracy_pct=round(accuracy_pct, 1),
            score=score,
            difficulty_tier=self._tier,
            game_mode=self._game_mode,
            total_words=len(self._word_completion_times),
            total_chars=total_chars,
            duration_secs=round(duration, 2),
            accuracy_tier=accuracy_tier,
        )

        return GhostRecording(
            meta=meta,
            word_list=self._word_list,
            keystroke_events=self._events,
            error_positions=self._error_positions,
            accuracy_heatmap=heatmap,
            word_completion_times=self._word_completion_times,
        )

    # ── Storage ────────────────────────────────────────────────────────────

    def save_ghost(self, recording: GhostRecording) -> str:
        """
        Save a ghost to disk (compressed JSON).
        Enforces MAX_PERSONAL_GHOSTS limit.

        :return: Path to saved file.
        """
        # Prune old ghosts if over limit
        existing = self.list_ghosts()
        if len(existing) >= MAX_PERSONAL_GHOSTS:
            # Remove lowest-scoring ghost
            existing.sort(key=lambda g: g.meta.score)
            self.delete_ghost(existing[0].meta.ghost_id)

        data = self._recording_to_dict(recording)
        filename = f"ghost_{recording.meta.ghost_id}.json.gz"
        filepath = os.path.join(self.ghost_dir, filename)
        compressed = gzip.compress(json.dumps(data).encode("utf-8"))
        with open(filepath, "wb") as f:
            f.write(compressed)
        return filepath

    def list_ghosts(self) -> List[GhostRecording]:
        """Return all stored personal ghosts sorted by score (desc)."""
        ghosts = []
        for fname in os.listdir(self.ghost_dir):
            if fname.startswith("ghost_") and fname.endswith(".json.gz"):
                path = os.path.join(self.ghost_dir, fname)
                g = self._load_ghost_file(path)
                if g:
                    ghosts.append(g)
        ghosts.sort(key=lambda g: g.meta.score, reverse=True)
        return ghosts

    def get_best_ghost(self) -> Optional[GhostRecording]:
        """Return personal best ghost (highest score)."""
        ghosts = self.list_ghosts()
        return ghosts[0] if ghosts else None

    def delete_ghost(self, ghost_id: str) -> bool:
        """Delete a ghost file by ID. Returns True on success."""
        for fname in os.listdir(self.ghost_dir):
            if ghost_id in fname:
                os.remove(os.path.join(self.ghost_dir, fname))
                return True
        return False

    # ── Playback ──────────────────────────────────────────────────────────

    def start_playback(self, recording: GhostRecording) -> GhostPlayback:
        """Create a GhostPlayback object ready to race against."""
        return GhostPlayback(recording=recording, start_time=time.time())

    # ── Export / Import ───────────────────────────────────────────────────

    def export_to_file(self, recording: GhostRecording, filepath: str) -> None:
        """Export a ghost to an arbitrary file path for sharing."""
        data = self._recording_to_dict(recording)
        compressed = gzip.compress(json.dumps(data).encode("utf-8"))
        with open(filepath, "wb") as f:
            f.write(compressed)

    def import_from_file(self, filepath: str) -> Optional[GhostRecording]:
        """Import a ghost from a shared file."""
        return self._load_ghost_file(filepath)

    def encode_qr_payload(self, recording: GhostRecording) -> str:
        """
        Encode a ghost to a compact base64 string suitable for QR embedding.
        Only includes metadata + completion times (not full keystrokes).
        """
        slim = {
            "meta": asdict(recording.meta),
            "words": recording.word_list[:20],  # truncate for QR size
            "times": recording.word_completion_times[:20],
            "heatmap": dict(list(recording.accuracy_heatmap.items())[:10]),
        }
        payload = json.dumps(slim, separators=(",", ":"))
        compressed = gzip.compress(payload.encode("utf-8"))
        return base64.urlsafe_b64encode(compressed).decode("ascii")

    def decode_qr_payload(self, payload: str) -> Optional[GhostRecording]:
        """Decode a QR payload string into a slim GhostRecording."""
        try:
            compressed = base64.urlsafe_b64decode(payload.encode("ascii"))
            data = json.loads(gzip.decompress(compressed).decode("utf-8"))
            meta = GhostMeta(**data["meta"])
            return GhostRecording(
                meta=meta,
                word_list=data.get("words", []),
                keystroke_events=[],
                error_positions={},
                accuracy_heatmap=data.get("heatmap", {}),
                word_completion_times=data.get("times", []),
            )
        except Exception:
            return None

    # ── Helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _recording_to_dict(recording: GhostRecording) -> dict:
        return {
            "meta": asdict(recording.meta),
            "word_list": recording.word_list,
            "keystroke_events": [asdict(e) for e in recording.keystroke_events],
            "error_positions": recording.error_positions,
            "accuracy_heatmap": recording.accuracy_heatmap,
            "word_completion_times": recording.word_completion_times,
        }

    def _load_ghost_file(self, filepath: str) -> Optional[GhostRecording]:
        try:
            with open(filepath, "rb") as f:
                raw = f.read()
            # Support both compressed and plain JSON
            try:
                data = json.loads(gzip.decompress(raw).decode("utf-8"))
            except Exception:
                data = json.loads(raw.decode("utf-8"))

            meta = GhostMeta(**data["meta"])
            events = [KeystrokeEvent(**e) for e in data.get("keystroke_events", [])]
            return GhostRecording(
                meta=meta,
                word_list=data.get("word_list", []),
                keystroke_events=events,
                error_positions=data.get("error_positions", {}),
                accuracy_heatmap=data.get("accuracy_heatmap", {}),
                word_completion_times=data.get("word_completion_times", []),
            )
        except Exception as exc:
            print(f"[GhostManager] Failed to load {filepath}: {exc}")
            return None
