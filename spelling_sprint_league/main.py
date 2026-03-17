"""
main.py - Spelling Sprint League
Main application entry point.
Contains all screen classes, GameEngine, RankManager, SoundManager, and app bootstrap.

Author: Spelling Sprint League Team
Version: 1.0
Target: Android 8.0+ via Buildozer / Kivy 2.1
"""

# ─────────────────────────────────────────────────────────────────────────────
# Standard imports
# ─────────────────────────────────────────────────────────────────────────────
import json
import os
import time
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

# ─────────────────────────────────────────────────────────────────────────────
# Kivy configuration (must precede kivy imports)
# ─────────────────────────────────────────────────────────────────────────────
os.environ.setdefault("KIVY_NO_ENV_CONFIG", "1")

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager, SlideTransition, FadeTransition
from kivy.uix.textinput import TextInput
from kivy.animation import Animation
from kivy.properties import NumericProperty, StringProperty, BooleanProperty

# ─────────────────────────────────────────────────────────────────────────────
# Local modules
# ─────────────────────────────────────────────────────────────────────────────
from word_bank import WordBank
from sentence_bank import SentenceBank
from accuracy_tracker import AccuracyTracker, AccuracyReport
from ghost_manager import GhostManager, GhostRecording, GhostPlayback
from network_manager import NetworkManager, MsgType, Role

# ─────────────────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.expanduser("~"), "SpellingSprint")
STATS_FILE = os.path.join(DATA_DIR, "stats.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
os.makedirs(DATA_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
SPRINT_DURATION = 60
SENTENCE_RACE_DURATION = 90
STREAK_THRESHOLDS = [5, 10, 15]

TIER_CONFIG = [
    {"name": "Bronze",   "emoji": "🥉", "min_wpm": 0,  "max_wpm": 20, "min_acc": 0.0,  "color": (0.8, 0.55, 0.2, 1)},
    {"name": "Silver",   "emoji": "🥈", "min_wpm": 21, "max_wpm": 35, "min_acc": 60.0, "color": (0.75, 0.75, 0.75, 1)},
    {"name": "Gold",     "emoji": "🥇", "min_wpm": 36, "max_wpm": 50, "min_acc": 75.0, "color": (1, 0.84, 0, 1)},
    {"name": "Platinum", "emoji": "💎", "min_wpm": 51, "max_wpm": 70, "min_acc": 85.0, "color": (0.68, 0.85, 0.9, 1)},
    {"name": "Diamond",  "emoji": "🔷", "min_wpm": 71, "max_wpm": 999,"min_acc": 90.0, "color": (0.4, 0.85, 1, 1)},
]

ACHIEVEMENTS = [
    {"id": "first_perfect",   "title": "Perfectionist",     "desc": "Achieve 100% accuracy in a game",    "emoji": "✨"},
    {"id": "speed_demon",     "title": "Speed Demon",       "desc": "Reach 60+ WPM in a single game",     "emoji": "⚡"},
    {"id": "marathon",        "title": "Marathon",          "desc": "Type 100 words in a single game",    "emoji": "🏃"},
    {"id": "error_free_50",   "title": "Error Free",        "desc": "Complete 50 words without mistakes", "emoji": "🎯"},
    {"id": "social_starter",  "title": "Social Starter",    "desc": "Complete your first local race",     "emoji": "👥"},
    {"id": "lan_legend",      "title": "LAN Legend",        "desc": "Win 10 local multiplayer races",     "emoji": "🌐"},
    {"id": "party_host",      "title": "Party Host",        "desc": "Host 5 multiplayer games",           "emoji": "🎮"},
    {"id": "ghost_buster",    "title": "Ghost Buster",      "desc": "Beat 10 ghost recordings",           "emoji": "👻"},
    {"id": "sharing_caring",  "title": "Sharing is Caring", "desc": "Export 5 ghost recordings",          "emoji": "📤"},
    {"id": "sentence_master", "title": "Sentence Master",   "desc": "Win 5 sentence races",               "emoji": "📝"},
    {"id": "precision_player","title": "Precision Player",  "desc": "90%+ accuracy in 10 races",          "emoji": "🎯"},
]


# ═══════════════════════════════════════════════════════════════════════════════
# GAME ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class GameEngine:
    """
    Core game logic: timer, scoring, WPM calculation, streak multiplier.
    Instantiated fresh for every race.
    """

    def __init__(
        self,
        duration: int = SPRINT_DURATION,
        mode: str = "sprint",
        tier: str = "bronze",
    ) -> None:
        self.duration = duration
        self.mode = mode
        self.tier = tier

        self.score: int = 0
        self.words_done: int = 0
        self.chars_typed: int = 0
        self.streak: int = 0
        self.multiplier: float = 1.0
        self.start_time: float = 0.0
        self.end_time: float = 0.0
        self.running: bool = False
        self.paused: bool = False
        self._word_bank = WordBank()
        self._sentence_bank = SentenceBank()
        self._accuracy_tracker = AccuracyTracker()

        self.word_list: List[str] = []
        self.sentence_list: List[Dict] = []
        self.current_index: int = 0

    def start(self, word_list: Optional[List[str]] = None, sentence_list: Optional[List[Dict]] = None) -> None:
        self._accuracy_tracker.reset()
        self._word_bank.reset()
        self.score = 0
        self.words_done = 0
        self.chars_typed = 0
        self.streak = 0
        self.multiplier = 1.0
        self.current_index = 0
        self.running = True
        self.start_time = time.time()

        if self.mode in ("sentence", "sentence_race"):
            self.sentence_list = sentence_list or self._sentence_bank.get_sentence_list(self.tier, 20)
        else:
            self.word_list = word_list or self._word_bank.get_word_list(self.tier, 80)

    def stop(self) -> None:
        self.running = False
        self.end_time = time.time()

    @property
    def elapsed(self) -> float:
        if not self.running:
            return self.end_time - self.start_time
        return time.time() - self.start_time

    @property
    def remaining(self) -> float:
        return max(0.0, self.duration - self.elapsed)

    @property
    def timer_frac(self) -> float:
        return self.remaining / self.duration

    @property
    def is_time_up(self) -> bool:
        return self.elapsed >= self.duration

    @property
    def current_word(self) -> str:
        if self.mode in ("sentence", "sentence_race"):
            if self.current_index < len(self.sentence_list):
                return self.sentence_list[self.current_index]["text"]
            return ""
        if self.current_index < len(self.word_list):
            return self.word_list[self.current_index]
        extra = self._word_bank.get_word(self.tier)
        self.word_list.append(extra)
        return extra

    def advance_word(self) -> str:
        word = self.current_word
        self.words_done += 1
        self.current_index += 1
        self._update_streak_and_score(word)
        self._accuracy_tracker.complete_word()
        return self.current_word

    def _update_streak_and_score(self, word: str) -> None:
        self.streak += 1
        if self.streak >= 15:
            self.multiplier = 2.0
        elif self.streak >= 10:
            self.multiplier = 1.5
        elif self.streak >= 5:
            self.multiplier = 1.2
        else:
            self.multiplier = 1.0

        base = 10 * len(word.split()) if self.mode in ("sentence", "sentence_race") else 10
        speed_bonus = max(0, int((self.remaining / self.duration) * 5))
        self.score += int((base + speed_bonus) * self.multiplier)

    def break_streak(self) -> None:
        self.streak = 0
        self.multiplier = 1.0

    def record_char(self, char: str, is_correct: bool, position: int = 0) -> None:
        self.chars_typed += 1
        self._accuracy_tracker.record_char(char, is_correct, position)

    def record_backspace(self, position: int = 0) -> None:
        self._accuracy_tracker.record_backspace(position)

    def start_word(self, word: str) -> None:
        self._accuracy_tracker.start_word(word)

    @property
    def accuracy(self) -> float:
        return self._accuracy_tracker.current_accuracy()

    def generate_report(self) -> AccuracyReport:
        return self._accuracy_tracker.generate_report()

    @property
    def wpm(self) -> float:
        mins = max(0.01, self.elapsed / 60.0)
        return round((self.chars_typed / 5.0) / mins, 1)

    def final_score(self) -> int:
        report = self.generate_report()
        score = self.score + report.bonus_points
        if report.penalty_pct < 0:
            score = int(score * (1 + report.penalty_pct / 100.0))
        return max(0, score)


# ═══════════════════════════════════════════════════════════════════════════════
# RANK MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class RankManager:

    def __init__(self) -> None:
        self.stats: Dict = self._load_stats()

    def _load_stats(self) -> Dict:
        defaults = {
            "games_played": 0,
            "total_words": 0,
            "total_chars": 0,
            "wpm_history": [],
            "accuracy_history": [],
            "best_wpm": 0.0,
            "best_accuracy": 0.0,
            "best_score": 0,
            "mp_wins": 0,
            "mp_games": 0,
            "sentence_wins": 0,
            "ghost_races": 0,
            "ghost_wins": 0,
            "ghosts_exported": 0,
            "consecutive_high_acc": 0,
            "achievements": [],
            "player_name": "Player",
        }
        if os.path.exists(STATS_FILE):
            try:
                with open(STATS_FILE, "r") as f:
                    loaded = json.load(f)
                defaults.update(loaded)
            except Exception:
                pass
        return defaults

    def save_stats(self) -> None:
        try:
            with open(STATS_FILE, "w") as f:
                json.dump(self.stats, f, indent=2)
        except Exception as e:
            print(f"[RankManager] save_stats error: {e}")

    def record_game(self, wpm: float, accuracy: float, score: int, words: int, mode: str = "sprint") -> None:
        s = self.stats
        s["games_played"] += 1
        s["total_words"] += words
        s["best_wpm"] = max(s["best_wpm"], wpm)
        s["best_accuracy"] = max(s["best_accuracy"], accuracy)
        s["best_score"] = max(s["best_score"], score)
        s["wpm_history"].append(round(wpm, 1))
        s["accuracy_history"].append(round(accuracy, 1))
        s["wpm_history"] = s["wpm_history"][-30:]
        s["accuracy_history"] = s["accuracy_history"][-30:]

        if accuracy >= 100.0:
            self._unlock("first_perfect")
        if wpm >= 60.0:
            self._unlock("speed_demon")
        if words >= 100:
            self._unlock("marathon")
        if accuracy >= 90.0:
            s["consecutive_high_acc"] = s.get("consecutive_high_acc", 0) + 1
            if s["consecutive_high_acc"] >= 10:
                self._unlock("precision_player")
        else:
            s["consecutive_high_acc"] = 0
        if mode == "sentence" and s.get("sentence_wins", 0) >= 5:
            self._unlock("sentence_master")
        self.save_stats()

    def record_mp_result(self, won: bool, is_host: bool) -> None:
        if won:
            self.stats["mp_wins"] = self.stats.get("mp_wins", 0) + 1
            if self.stats["mp_wins"] == 1:
                self._unlock("social_starter")
            if self.stats["mp_wins"] >= 10:
                self._unlock("lan_legend")
        if is_host:
            hosted = self.stats.get("times_hosted", 0) + 1
            self.stats["times_hosted"] = hosted
            if hosted >= 5:
                self._unlock("party_host")
        self.stats["mp_games"] = self.stats.get("mp_games", 0) + 1
        self.save_stats()

    def record_ghost_result(self, won: bool) -> None:
        self.stats["ghost_races"] = self.stats.get("ghost_races", 0) + 1
        if won:
            self.stats["ghost_wins"] = self.stats.get("ghost_wins", 0) + 1
            if self.stats["ghost_wins"] >= 10:
                self._unlock("ghost_buster")
        self.save_stats()

    def record_ghost_export(self) -> None:
        n = self.stats.get("ghosts_exported", 0) + 1
        self.stats["ghosts_exported"] = n
        if n >= 5:
            self._unlock("sharing_caring")
        self.save_stats()

    def _unlock(self, achievement_id: str) -> Optional[Dict]:
        if achievement_id not in self.stats.get("achievements", []):
            self.stats.setdefault("achievements", []).append(achievement_id)
            return next((a for a in ACHIEVEMENTS if a["id"] == achievement_id), None)
        return None

    @property
    def current_tier(self) -> Dict:
        wpm_history = self.stats.get("wpm_history", [])
        acc_history = self.stats.get("accuracy_history", [])
        avg_wpm = sum(wpm_history[-10:]) / max(1, len(wpm_history[-10:]))
        avg_acc = sum(acc_history[-10:]) / max(1, len(acc_history[-10:]))
        best_tier = TIER_CONFIG[0]
        for tier in TIER_CONFIG:
            if avg_wpm >= tier["min_wpm"] and avg_acc >= tier["min_acc"]:
                best_tier = tier
        return best_tier

    @property
    def avg_wpm(self) -> float:
        h = self.stats.get("wpm_history", [])[-10:]
        return round(sum(h) / max(1, len(h)), 1)

    @property
    def avg_accuracy(self) -> float:
        h = self.stats.get("accuracy_history", [])[-10:]
        return round(sum(h) / max(1, len(h)), 1)

    @property
    def word_difficulty_tier(self) -> str:
        return self.current_tier["name"].lower()

    @property
    def unlocked_achievements(self) -> List[Dict]:
        ids = self.stats.get("achievements", [])
        return [a for a in ACHIEVEMENTS if a["id"] in ids]


# ═══════════════════════════════════════════════════════════════════════════════
# SOUND MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class SoundManager:
    """
    Manages game audio.
    Place these files in your assets/ folder:
      assets/keypress.wav   - short click sound
      assets/success.wav    - chime for correct word
      assets/error.wav      - buzz for wrong word
      assets/beep.wav       - countdown beep
      assets/victory.wav    - race win fanfare
      assets/ghost_defeated.wav - ghost beaten sound
    Falls back silently if any file is missing.
    """

    def __init__(self) -> None:
        self.sound_enabled: bool = True
        self.vibration_enabled: bool = True
        self._sounds: Dict = {}
        self._try_load_sounds()

    def _try_load_sounds(self) -> None:
        """Load all sound files from assets/ folder. Skips missing files silently."""
        try:
            from kivy.core.audio import SoundLoader

            sound_files = {
                "keypress":      "assets/keypress.wav",
                "success":       "assets/success.wav",
                "error":         "assets/error.wav",
                "beep":          "assets/beep.wav",
                "victory":       "assets/victory.wav",
                "ghost_defeated":"assets/ghost_defeated.wav",
            }

            for name, path in sound_files.items():
                if os.path.exists(path):
                    sound = SoundLoader.load(path)
                    if sound:
                        self._sounds[name] = sound
                        print(f"[SoundManager] Loaded: {path}")
                    else:
                        print(f"[SoundManager] Failed to load: {path}")
                else:
                    print(f"[SoundManager] Not found (skipping): {path}")

        except Exception as e:
            print(f"[SoundManager] Audio init failed: {e}")

    def play(self, name: str) -> None:
        """Play a sound by name. Does nothing if sound is disabled or file missing."""
        if not self.sound_enabled:
            return
        sound = self._sounds.get(name)
        if sound:
            try:
                # Stop and rewind before playing so rapid triggers work
                sound.stop()
                sound.play()
            except Exception as e:
                print(f"[SoundManager] Play error ({name}): {e}")

    def vibrate(self, duration: float = 0.05) -> None:
        """Vibrate the device (Android only). Ignored on desktop."""
        if not self.vibration_enabled:
            return
        try:
            from kivy.utils import platform
            if platform == "android":
                from jnius import autoclass  # type: ignore
                context = autoclass("org.kivy.android.PythonActivity").mActivity
                vibrator = context.getSystemService("vibrator")
                vibrator.vibrate(int(duration * 1000))
        except Exception:
            pass  # Silently skip on non-Android

    # ── Named helpers ──────────────────────────────────────────────────────

    def keypress(self) -> None:
        """Play keypress click sound."""
        self.play("keypress")

    def word_correct(self) -> None:
        """Play success chime for correct word."""
        self.play("success")

    def word_error(self) -> None:
        """Play error buzz and vibrate for wrong word."""
        self.play("error")
        self.vibrate(0.08)

    def countdown_beep(self) -> None:
        """Play countdown beep (3-2-1)."""
        self.play("beep")

    def victory(self) -> None:
        """Play victory fanfare."""
        self.play("victory")

    def ghost_defeated(self) -> None:
        """Play ghost defeated sound."""
        self.play("ghost_defeated")

    def reload(self) -> None:
        """Reload all sounds (call after settings change)."""
        self._sounds.clear()
        self._try_load_sounds()


# ═══════════════════════════════════════════════════════════════════════════════
# BASE SCREEN
# ═══════════════════════════════════════════════════════════════════════════════

class BaseScreen(Screen):

    def go_back(self, *args) -> None:
        App.get_running_app().go_to_screen("menu", direction="right")

    def show_toast(self, message: str, color: tuple = (0.2, 0.6, 1, 1), duration: float = 2.5) -> None:
        popup = Popup(
            title="",
            content=Label(
                text=message,
                font_size=sp(15),
                color=(1, 1, 1, 1),
                halign="center",
            ),
            size_hint=(0.8, None),
            height=dp(80),
            background_color=(*color[:3], 0.92),
            separator_height=0,
            auto_dismiss=True,
        )
        popup.open()
        Clock.schedule_once(lambda dt: popup.dismiss(), duration)


# ═══════════════════════════════════════════════════════════════════════════════
# SPLASH SCREEN
# ═══════════════════════════════════════════════════════════════════════════════

class SplashScreen(BaseScreen):
    def on_enter(self, *args) -> None:
        Clock.schedule_once(self._go_to_menu, 2.0)

    def _go_to_menu(self, dt) -> None:
        App.get_running_app().go_to_screen("menu")


# ═══════════════════════════════════════════════════════════════════════════════
# MENU SCREEN
# ═══════════════════════════════════════════════════════════════════════════════

class MenuScreen(BaseScreen):
    def on_enter(self, *args) -> None:
        app = App.get_running_app()
        tier = app.rank_manager.current_tier
        self.ids.rank_badge.text = f"{tier['emoji']} {tier['name']}"

    def go_sprint(self) -> None:
        app = App.get_running_app()
        app.prepare_solo_game("sprint")
        app.go_to_screen("solo_game")

    def go_league(self) -> None:
        app = App.get_running_app()
        app.prepare_solo_game("league")
        app.go_to_screen("solo_game")

    def go_practice(self) -> None:
        app = App.get_running_app()
        app.prepare_solo_game("practice")
        app.go_to_screen("solo_game")

    def go_multiplayer(self) -> None:
        App.get_running_app().go_to_screen("mp_hub")

    def go_ghost(self) -> None:
        App.get_running_app().go_to_screen("ghost_hub")

    def go_stats(self) -> None:
        App.get_running_app().go_to_screen("stats")

    def go_league_rank(self) -> None:
        App.get_running_app().go_to_screen("league_rank")

    def go_settings(self) -> None:
        App.get_running_app().go_to_screen("settings")


# ═══════════════════════════════════════════════════════════════════════════════
# SOLO GAME SCREEN
# ═══════════════════════════════════════════════════════════════════════════════

class SoloGameScreen(BaseScreen):

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._engine: Optional[GameEngine] = None
        self._clock_event = None
        self._ghost_manager: Optional[GhostManager] = None
        self._is_recording: bool = False
        self._countdown: int = 0

    def on_enter(self, *args) -> None:
        app = App.get_running_app()
        self._engine = app.active_engine
        self._ghost_manager = app.ghost_manager
        if self._engine:
            self._start_countdown()

    def _start_countdown(self) -> None:
        self._countdown = 3
        self._show_countdown()

    def _show_countdown(self, dt=None) -> None:
        if self._countdown > 0:
            self.ids.target_word_label.text = str(self._countdown)
            self.ids.target_word_label.font_size = sp(80)
            App.get_running_app().sound_manager.countdown_beep()
            self._countdown -= 1
            Clock.schedule_once(self._show_countdown, 1.0)
        else:
            self.ids.target_word_label.font_size = sp(48)
            self._begin_race()

    def _begin_race(self) -> None:
        engine = self._engine
        if not engine:
            return
        engine.start()
        engine.start_word(engine.current_word)
        self.ids.target_word_label.text = engine.current_word
        self.ids.mode_label.text = engine.mode.upper()
        self.ids.word_input.focus = True
        self.ids.word_input.text = ""

        app = App.get_running_app()
        self._ghost_manager.start_recording(
            word_list=engine.word_list,
            device_name=app.rank_manager.stats.get("player_name", "Player"),
            game_mode="word",
            tier=engine.tier,
        )
        self._is_recording = True
        self._clock_event = Clock.schedule_interval(self._tick, 0.1)

    def _tick(self, dt: float) -> None:
        engine = self._engine
        if not engine or not engine.running:
            return

        remaining = engine.remaining
        self._draw_bar(self.ids.timer_bar, engine.timer_frac, (0, 0.85, 1, 1))
        self.ids.timer_label.text = str(int(remaining))
        self.ids.score_label.text = str(engine.score)
        self.ids.streak_label.text = f"x{engine.multiplier:.1f}"

        acc = engine.accuracy
        self.ids.accuracy_label.text = f"{acc:.0f}%"

        from accuracy_tracker import AccuracyTracker as AT
        color_hex = AT.accuracy_color(acc)
        self.ids.accuracy_label.color = self._hex_to_rgba(color_hex)
        self.ids.acc_tier_label.text = AT.format_accuracy(acc)
        self.ids.words_done_label.text = f"{engine.words_done} word{'s' if engine.words_done != 1 else ''}"

        if engine.is_time_up and engine.mode != "practice":
            self._end_game()

    def _draw_bar(self, widget, frac: float, color: tuple) -> None:
        """Draw a filled progress bar on a plain Widget from Python."""
        from kivy.graphics import Color as KColor, RoundedRectangle as KRRect
        widget.canvas.clear()
        with widget.canvas:
            KColor(rgba=(0.12, 0.19, 0.32, 1))
            KRRect(pos=widget.pos, size=widget.size, radius=[dp(5)])
            KColor(rgba=color)
            KRRect(
                pos=widget.pos,
                size=(max(dp(6), widget.width * min(1.0, frac)), widget.height),
                radius=[dp(5)],
            )

    def on_input_text(self, instance: TextInput, value: str) -> None:
        engine = self._engine
        if not engine or not engine.running:
            return

        target = engine.current_word
        if len(value) > 0:
            char = value[-1]
            is_correct = len(value) <= len(target) and value == target[:len(value)]
            engine.record_char(char, is_correct, len(value) - 1)
            self._ghost_manager.record_keystroke(char, is_correct, len(value) - 1)
            App.get_running_app().sound_manager.keypress()

        if value.endswith(" ") or value.lower().strip() == target.lower():
            typed = value.strip().lower()
            if typed == target.lower():
                self._on_correct_word()
            else:
                self._on_wrong_word()
            instance.text = ""

    def _on_correct_word(self) -> None:
        engine = self._engine
        App.get_running_app().sound_manager.word_correct()
        self._ghost_manager.complete_word(engine.current_index)
        next_word = engine.advance_word()
        engine.start_word(next_word)
        self.ids.target_word_label.text = next_word
        self._flash_color((0, 0.78, 0.33, 0.4))

    def _on_wrong_word(self) -> None:
        engine = self._engine
        engine.break_streak()
        App.get_running_app().sound_manager.word_error()
        self._flash_color((1, 0.2, 0.2, 0.4))

    def _flash_color(self, color: tuple) -> None:
        lbl = self.ids.target_word_label
        lbl.color = color
        Clock.schedule_once(lambda dt: setattr(lbl, "color", (1, 1, 1, 1)), 0.15)

    def _end_game(self) -> None:
        if self._clock_event:
            self._clock_event.cancel()
        engine = self._engine
        engine.stop()

        app = App.get_running_app()
        app.sound_manager.victory()

        report = engine.generate_report()
        ghost = self._ghost_manager.stop_recording(
            wpm=engine.wpm,
            accuracy_pct=report.overall_pct,
            score=engine.final_score(),
            accuracy_tier=report.tier,
            player_name=app.rank_manager.stats.get("player_name", "Player"),
        )

        app.rank_manager.record_game(
            wpm=engine.wpm,
            accuracy=report.overall_pct,
            score=engine.final_score(),
            words=engine.words_done,
            mode=engine.mode,
        )

        app.last_result = {
            "wpm": engine.wpm,
            "accuracy": report.overall_pct,
            "score": engine.final_score(),
            "words": engine.words_done,
            "tier": report.tier_label,
            "mode": engine.mode,
            "ghost": ghost,
            "report": report,
        }

        app.go_to_screen("result", transition=FadeTransition())

    def quit_game(self) -> None:
        if self._clock_event:
            self._clock_event.cancel()
        if self._engine:
            self._engine.stop()
        App.get_running_app().go_to_screen("menu", direction="right")

    @staticmethod
    def _hex_to_rgba(hex_color: str) -> tuple:
        hex_color = hex_color.lstrip("#")
        r, g, b = (int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))
        return (r, g, b, 1.0)


# ═══════════════════════════════════════════════════════════════════════════════
# LOCAL MULTIPLAYER HUB SCREEN
# ═══════════════════════════════════════════════════════════════════════════════

class LocalMultiplayerHubScreen(BaseScreen):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._players: Dict[str, Dict] = {}
        self._is_host: bool = False
        self._game_mode: str = "word"

    def on_enter(self, *args) -> None:
        app = App.get_running_app()
        ip = app.network_manager.get_local_ip()
        self.ids.ip_display.text = f"Your IP: {ip}"
        self.ids.connection_status_label.text = "Ready to play"
        self._update_player_slots()

    def show_host_type_selector(self) -> None:
        content = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(14))
        content.add_widget(Label(text="Choose Game Type", font_size=sp(20), bold=True,
                                 color=(1, 1, 1, 1), size_hint_y=None, height=dp(36)))

        popup = Popup(title="", separator_height=0, size_hint=(0.85, None), height=dp(240),
                      background_color=(0.06, 0.12, 0.22, 0.97))

        def _pick(mode: str) -> None:
            self._game_mode = mode
            self.ids.game_type_badge.text = "WORD RACE" if mode == "word" else "SENTENCE RACE"
            popup.dismiss()
            self._host_game()

        btn_word = Button(text="Word Race\n60 seconds, individual words",
                          font_size=sp(16), size_hint_y=None, height=dp(70),
                          background_color=(0, 0.78, 0.33, 1))
        btn_sent = Button(text="Sentence Race\n90 seconds, complete passages",
                          font_size=sp(16), size_hint_y=None, height=dp(70),
                          background_color=(0, 0.55, 0.85, 1))

        btn_word.bind(on_release=lambda *a: _pick("word"))
        btn_sent.bind(on_release=lambda *a: _pick("sentence"))

        content.add_widget(btn_word)
        content.add_widget(btn_sent)
        popup.content = content
        popup.open()

    def _host_game(self) -> None:
        app = App.get_running_app()
        app.network_manager.host_game(self._game_mode)
        self._is_host = True
        self.ids.connection_status_label.text = "Hosting... waiting for players"
        self.ids.start_race_btn.opacity = 1
        self.ids.start_race_btn.disabled = False
        self.show_toast("Hosting! Share your IP with friends.", (0, 0.6, 0.3, 1))

    def discover_hosts(self) -> None:
        self.ids.connection_status_label.text = "Searching for hosts..."
        self.show_toast("Scanning local network...", (0, 0.55, 0.85, 1))

        def _scan() -> None:
            hosts = App.get_running_app().network_manager.discover_hosts(timeout=4.0)
            Clock.schedule_once(lambda dt: self._show_host_list(hosts), 0)

        threading.Thread(target=_scan, daemon=True).start()

    def _show_host_list(self, hosts: List[Dict]) -> None:
        if not hosts:
            self.ids.connection_status_label.text = "No hosts found"
            self.show_toast("No hosts found. Try manual IP.", (0.8, 0.4, 0, 1))
            return
        content = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
        content.add_widget(Label(text="Select Host", font_size=sp(18), bold=True,
                                 color=(1, 1, 1, 1), size_hint_y=None, height=dp(32)))
        popup = Popup(title="", separator_height=0, size_hint=(0.85, None),
                      height=dp(80 + len(hosts) * 60),
                      background_color=(0.06, 0.12, 0.22, 0.97))
        for h in hosts:
            label = f"{h['name']} — {h['ip']} ({h.get('game_mode','word').upper()})"
            btn = Button(text=label, font_size=sp(14), size_hint_y=None, height=dp(52),
                         background_color=(0.1, 0.2, 0.35, 1))
            btn.bind(on_release=lambda *a, ip=h["ip"]: (popup.dismiss(), self._join(ip)))
            content.add_widget(btn)
        popup.content = content
        popup.open()

    def _join(self, host_ip: str) -> None:
        nm = App.get_running_app().network_manager
        nm.on_event = self._on_network_event
        if nm.join_game(host_ip):
            self.ids.connection_status_label.text = f"Joined: {host_ip}"
            self.show_toast("Connected to host!", (0, 0.78, 0.33, 1))
        else:
            self.show_toast("Connection failed. Check IP.", (0.9, 0.2, 0.2, 1))

    def show_manual_ip_dialog(self) -> None:
        content = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        content.add_widget(Label(text="Enter Host IP Address", font_size=sp(16),
                                 color=(1, 1, 1, 1), size_hint_y=None, height=dp(28)))
        ti = TextInput(hint_text="e.g. 192.168.1.100", font_size=sp(18),
                       size_hint_y=None, height=dp(46), multiline=False)
        content.add_widget(ti)
        popup = Popup(title="", separator_height=0, size_hint=(0.85, None), height=dp(180),
                      background_color=(0.06, 0.12, 0.22, 0.97))
        btn = Button(text="Connect", font_size=sp(16), size_hint_y=None, height=dp(48),
                     background_color=(0, 0.78, 0.33, 1))
        btn.bind(on_release=lambda *a: (popup.dismiss(), self._join(ti.text.strip())))
        content.add_widget(btn)
        popup.content = content
        popup.open()

    def start_race(self) -> None:
        app = App.get_running_app()
        engine = GameEngine(
            duration=SPRINT_DURATION if self._game_mode == "word" else SENTENCE_RACE_DURATION,
            mode=self._game_mode,
            tier=app.rank_manager.word_difficulty_tier,
        )
        engine.start()
        app.active_engine = engine
        app.network_manager.host_start_race(word_list=engine.word_list)
        app.mp_game_mode = self._game_mode
        app.go_to_screen("mp_game")

    def _on_network_event(self, msg: Dict) -> None:
        Clock.schedule_once(lambda dt: self._handle_event(msg), 0)

    def _handle_event(self, msg: Dict) -> None:
        t = msg.get("type")
        if t == MsgType.PLAYER_JOIN:
            pid = msg.get("ip") or msg.get("_sender_id", "unknown")
            self._players[pid] = {"name": msg.get("name", "Player"), "ip": pid}
            self._update_player_slots()
        elif t == MsgType.PLAYER_DISCONNECT:
            self._players.pop(msg.get("player_id"), None)
            self._update_player_slots()
        elif t == MsgType.GAME_START:
            app = App.get_running_app()
            app.mp_game_mode = msg.get("game_mode", "word")
            engine = GameEngine(
                duration=SPRINT_DURATION if app.mp_game_mode == "word" else SENTENCE_RACE_DURATION,
                mode=app.mp_game_mode,
                tier=app.rank_manager.word_difficulty_tier,
            )
            if "word_list" in msg:
                engine.start(word_list=msg["word_list"])
            else:
                engine.start()
            app.active_engine = engine
            app.go_to_screen("mp_game")

    def _update_player_slots(self) -> None:
        app = App.get_running_app()
        my_name = app.rank_manager.stats.get("player_name", "You")
        slots = [self.ids.slot1_label, self.ids.slot2_label,
                 self.ids.slot3_label, self.ids.slot4_label]
        slots[0].text = f"You: {my_name}"
        slots[0].color = (0, 0.85, 1, 1)
        players = list(self._players.values())
        for i, slot in enumerate(slots[1:], 0):
            if i < len(players):
                slot.text = players[i]['name']
                slot.color = (0.4, 0.9, 0.4, 1)
            else:
                slot.text = "Empty"
                slot.color = (0.4, 0.5, 0.6, 1)
        if self._is_host and len(self._players) >= 1:
            self.ids.start_race_btn.opacity = 1
            self.ids.start_race_btn.disabled = False


# ═══════════════════════════════════════════════════════════════════════════════
# LOCAL MULTIPLAYER GAME SCREEN
# ═══════════════════════════════════════════════════════════════════════════════

class LocalMultiplayerGameScreen(BaseScreen):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._engine: Optional[GameEngine] = None
        self._clock_event = None
        self._opponent_data: Dict[str, Dict] = {}
        self._progress_event = None

    def on_enter(self, *args) -> None:
        app = App.get_running_app()
        self._engine = app.active_engine
        app.network_manager.on_event = self._on_network_event
        self._start_countdown()

    def _start_countdown(self) -> None:
        self._countdown_n = 3
        self._do_countdown()

    def _do_countdown(self, dt=None) -> None:
        if self._countdown_n > 0:
            self.ids.race_status_label.text = f"Race starts in {self._countdown_n}..."
            self.ids.mp_target_label.text = str(self._countdown_n)
            App.get_running_app().sound_manager.countdown_beep()
            self._countdown_n -= 1
            Clock.schedule_once(self._do_countdown, 1.0)
        else:
            self.ids.race_status_label.text = "GO!"
            self._begin_race()

    def _begin_race(self) -> None:
        engine = self._engine
        if not engine:
            return
        self.ids.mp_target_label.text = engine.current_word
        self.ids.mp_word_input.focus = True
        self.ids.mp_word_input.text = ""
        self._clock_event = Clock.schedule_interval(self._tick, 0.1)
        self._progress_event = Clock.schedule_interval(self._send_progress, 0.5)

    def _tick(self, dt: float) -> None:
        engine = self._engine
        if not engine or not engine.running:
            return
        self.ids.mp_timer_label.text = str(int(engine.remaining))
        self.ids.mp_score_label.text = str(engine.score)
        self.ids.mp_accuracy_label.text = f"{engine.accuracy:.0f}%"

        my_words = engine.words_done
        rank = 1 + sum(
            1 for op in self._opponent_data.values()
            if op.get("words_done", 0) > my_words
        )
        suffixes = {1: "st", 2: "nd", 3: "rd"}
        self.ids.mp_rank_label.text = f"{rank}{suffixes.get(rank, 'th')}"
        self.ids.race_status_label.text = "Leading!" if rank == 1 else \
            f"Behind by {max(op.get('words_done',0) for op in self._opponent_data.values()) - my_words}!"

        self._update_opponent_bars()
        if engine.is_time_up:
            self._end_game()

    def _update_opponent_bars(self) -> None:
        engine = self._engine
        max_words = max(1, max(
            [engine.words_done] + [o.get("words_done", 0) for o in self._opponent_data.values()]
        ))
        bars  = [self.ids.opp1_bar,  self.ids.opp2_bar,  self.ids.opp3_bar]
        names = [self.ids.opp1_name, self.ids.opp2_name, self.ids.opp3_name]
        accs  = [self.ids.opp1_acc,  self.ids.opp2_acc,  self.ids.opp3_acc]
        from kivy.graphics import Color as KColor, RoundedRectangle as KRRect
        for i, (pid, data) in enumerate(list(self._opponent_data.items())[:3]):
            names[i].text = data.get("name", f"P{i+2}")[:8]
            accs[i].text  = f"{data.get('accuracy_pct', 0):.0f}%"
            pct = data.get("words_done", 0) / max_words
            bar = bars[i]
            bar.canvas.clear()
            with bar.canvas:
                KColor(rgba=(0.12, 0.19, 0.32, 1))
                KRRect(pos=bar.pos, size=bar.size, radius=[dp(4)])
                KColor(rgba=(0, 0.85, 1, 1))
                KRRect(pos=bar.pos, size=(bar.width * pct, bar.height), radius=[dp(4)])

    def _send_progress(self, dt: float) -> None:
        engine = self._engine
        if not engine:
            return
        App.get_running_app().network_manager.send_progress(
            words_done=engine.words_done,
            score=engine.score,
            accuracy_pct=engine.accuracy,
        )

    def on_input_text(self, instance: TextInput, value: str) -> None:
        engine = self._engine
        if not engine or not engine.running:
            return
        target = engine.current_word
        if len(value) > 0:
            engine.record_char(value[-1], value == target[:len(value)], len(value) - 1)
        if value.endswith(" ") or value.lower().strip() == target.lower():
            if value.strip().lower() == target.lower():
                next_word = engine.advance_word()
                engine.start_word(next_word)
                self.ids.mp_target_label.text = next_word
                App.get_running_app().sound_manager.word_correct()
            else:
                engine.break_streak()
            instance.text = ""

    def _on_network_event(self, msg: Dict) -> None:
        Clock.schedule_once(lambda dt: self._handle_net(msg), 0)

    def _handle_net(self, msg: Dict) -> None:
        t = msg.get("type")
        if t == MsgType.PROGRESS:
            pid = msg.get("player_id", "unknown")
            if pid != App.get_running_app().network_manager.local_ip:
                self._opponent_data[pid] = {
                    "name": msg.get("name", pid[:6]),
                    "words_done": msg.get("words_done", 0),
                    "score": msg.get("score", 0),
                    "accuracy_pct": msg.get("accuracy_pct", 100),
                }
        elif t == MsgType.WORD_SYNC:
            self.ids.mp_target_label.text = msg.get("word", "")
        elif t == MsgType.GAME_END:
            self._end_game()
        elif t == MsgType.PLAYER_DISCONNECT:
            pid = msg.get("player_id")
            if pid in self._opponent_data:
                self._opponent_data[pid]["disconnected"] = True

    def _end_game(self) -> None:
        if self._clock_event:
            self._clock_event.cancel()
        if self._progress_event:
            self._progress_event.cancel()
        engine = self._engine
        if engine:
            engine.stop()
        app = App.get_running_app()
        report = engine.generate_report() if engine else None

        final_scores = [{
            "name": app.rank_manager.stats.get("player_name", "You"),
            "score": engine.final_score() if engine else 0,
            "wpm": engine.wpm if engine else 0,
            "accuracy": report.overall_pct if report else 0,
            "is_me": True,
        }]
        for pid, data in self._opponent_data.items():
            final_scores.append({
                "name": data.get("name", pid[:6]),
                "score": data.get("score", 0),
                "wpm": 0,
                "accuracy": data.get("accuracy_pct", 0),
                "is_me": False,
            })
        final_scores.sort(key=lambda x: x["score"], reverse=True)
        app.last_mp_result = {"scores": final_scores, "mode": app.mp_game_mode}
        if app.network_manager.is_host:
            app.network_manager.send_game_end(final_scores)
        app.go_to_screen("mp_result", transition=FadeTransition())


# ═══════════════════════════════════════════════════════════════════════════════
# GHOST RACE HUB SCREEN
# ═══════════════════════════════════════════════════════════════════════════════

class GhostRaceHubScreen(BaseScreen):
    def on_enter(self, *args) -> None:
        self._refresh_ghost_list()

    def _refresh_ghost_list(self) -> None:
        app = App.get_running_app()
        container = self.ids.ghost_list_container
        container.clear_widgets()
        ghosts = app.ghost_manager.list_ghosts()
        if not ghosts:
            container.add_widget(Label(
                text="No ghosts saved yet.\nPlay a solo game to create your first ghost!",
                font_size=sp(15), color=(0.5, 0.6, 0.7, 1),
                size_hint_y=None, height=dp(60), halign="center",
            ))
            return
        for g in ghosts:
            row = BoxLayout(size_hint_y=None, height=dp(54), spacing=dp(10))
            row.add_widget(Label(text=f"{g.meta.name}\n{g.meta.date_recorded}",
                                 font_size=sp(13), color=(0.9, 0.9, 0.9, 1), size_hint_x=0.35))
            row.add_widget(Label(text=f"{g.meta.wpm} WPM\n{g.meta.accuracy_pct}% acc",
                                 font_size=sp(13), color=(0, 0.85, 1, 1), size_hint_x=0.3))
            race_btn  = Button(text="Race",  font_size=sp(13), size_hint_x=0.17, background_color=(0.75, 0.4, 1, 1))
            share_btn = Button(text="Share", font_size=sp(13), size_hint_x=0.18, background_color=(0.1, 0.4, 0.7, 1))
            race_btn.bind(on_release=lambda *a, gr=g: self._start_ghost_race(gr))
            share_btn.bind(on_release=lambda *a, gr=g: self._share_ghost(gr))
            row.add_widget(race_btn)
            row.add_widget(share_btn)
            container.add_widget(row)

    def race_best_ghost(self) -> None:
        best = App.get_running_app().ghost_manager.get_best_ghost()
        if best:
            self._start_ghost_race(best)
        else:
            self.show_toast("No ghost saved yet! Play a solo game first.", (0.8, 0.4, 0, 1))

    def _start_ghost_race(self, recording: GhostRecording) -> None:
        app = App.get_running_app()
        app.active_ghost = recording
        app.ghost_playback = app.ghost_manager.start_playback(recording)
        engine = GameEngine(duration=SPRINT_DURATION, mode="sprint", tier=recording.meta.difficulty_tier)
        engine.start(word_list=recording.word_list)
        app.active_engine = engine
        app.go_to_screen("ghost_game")

    def _share_ghost(self, recording: GhostRecording) -> None:
        app = App.get_running_app()
        export_path = os.path.join(DATA_DIR, f"share_{recording.meta.ghost_id}.json.gz")
        app.ghost_manager.export_to_file(recording, export_path)
        app.rank_manager.record_ghost_export()
        self.show_toast(f"Ghost exported to:\n{export_path}", (0.75, 0.4, 1, 1))

    def import_ghost(self) -> None:
        self.show_toast("Place .json.gz ghost files in\n~/SpellingSprint/Ghosts/", (0.4, 0.6, 1, 1))

    def browse_community_ghosts(self) -> None:
        self.show_toast("Community ghosts require internet.\nSee README for details.", (0.4, 0.6, 1, 1))


# ═══════════════════════════════════════════════════════════════════════════════
# GHOST RACE GAME SCREEN
# ═══════════════════════════════════════════════════════════════════════════════

class GhostRaceGameScreen(BaseScreen):

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._engine: Optional[GameEngine] = None
        self._playback: Optional[GhostPlayback] = None
        self._clock_event = None

    def on_enter(self, *args) -> None:
        app = App.get_running_app()
        self._engine = app.active_engine
        self._playback = app.ghost_playback
        if self._engine:
            self._start()

    def _start(self) -> None:
        engine = self._engine
        pb = self._playback
        engine.start(word_list=pb.recording.word_list if pb else None)
        engine.start_word(engine.current_word)
        self.ids.ghost_target_label.text = engine.current_word
        self.ids.ghost_word_input.focus = True
        self.ids.ghost_word_input.text = ""
        self._clock_event = Clock.schedule_interval(self._tick, 0.1)

    def _draw_bar(self, widget, frac: float, color: tuple) -> None:
        from kivy.graphics import Color as KColor, RoundedRectangle as KRRect
        widget.canvas.clear()
        with widget.canvas:
            KColor(rgba=(0.12, 0.19, 0.32, 1))
            KRRect(pos=widget.pos, size=widget.size, radius=[dp(5)])
            KColor(rgba=color)
            KRRect(
                pos=widget.pos,
                size=(max(dp(6), widget.width * min(1.0, frac)), widget.height),
                radius=[dp(5)],
            )

    def _tick(self, dt: float) -> None:
        engine = self._engine
        if not engine or not engine.running:
            return
        pb = self._playback

        self.ids.ghost_timer_label.text = str(int(engine.remaining))
        self.ids.ghost_my_score_label.text = str(engine.score)
        self.ids.ghost_my_acc_label.text = f"{engine.accuracy:.0f}%"

        ghost_frac = 0.0
        if pb:
            pb.tick(time.time())
            total = len(pb.recording.word_list) or 1
            ghost_frac = min(1.0, pb.words_completed / total)
            self.ids.ghost_score_label.text = str(int(pb.words_completed * 10))

        my_total = len(engine.word_list) or 1
        my_frac = min(1.0, engine.words_done / my_total)

        self._draw_bar(self.ids.my_progress_bar,    my_frac,    (0, 0.85, 1, 1))
        self._draw_bar(self.ids.ghost_progress_bar, ghost_frac, (0.75, 0.4, 1, 0.8))

        if pb:
            diff = engine.words_done - pb.words_completed
            if diff > 0:
                self.ids.ghost_status_label.text = f"You're ahead by {diff}!"
                self.ids.ghost_status_label.color = (0, 0.85, 1, 1)
            elif diff < 0:
                self.ids.ghost_status_label.text = f"Ghost ahead by {abs(diff)}!"
                self.ids.ghost_status_label.color = (0.75, 0.4, 1, 1)
            else:
                self.ids.ghost_status_label.text = "Neck and neck!"
                self.ids.ghost_status_label.color = (1, 0.84, 0, 1)

        if engine.is_time_up:
            self._end_game()

    def on_input_text(self, instance: TextInput, value: str) -> None:
        engine = self._engine
        if not engine or not engine.running:
            return
        target = engine.current_word
        if len(value) > 0:
            engine.record_char(value[-1], value == target[:len(value)], len(value) - 1)
        if value.endswith(" ") or value.lower().strip() == target.lower():
            if value.strip().lower() == target.lower():
                next_word = engine.advance_word()
                engine.start_word(next_word)
                self.ids.ghost_target_label.text = next_word
                App.get_running_app().sound_manager.word_correct()
            else:
                engine.break_streak()
                App.get_running_app().sound_manager.word_error()
            instance.text = ""

    def _end_game(self) -> None:
        if self._clock_event:
            self._clock_event.cancel()
        engine = self._engine
        pb = self._playback
        engine.stop()

        won = (pb is None) or (engine.words_done >= pb.words_completed)
        app = App.get_running_app()
        if won:
            app.sound_manager.ghost_defeated()
        app.rank_manager.record_ghost_result(won)
        report = engine.generate_report()
        app.last_result = {
            "wpm": engine.wpm,
            "accuracy": report.overall_pct,
            "score": engine.final_score(),
            "words": engine.words_done,
            "tier": report.tier_label,
            "mode": "ghost",
            "ghost_won": won,
            "ghost_name": pb.recording.meta.name if pb else "Ghost",
            "ghost_words": pb.words_completed if pb else 0,
        }
        app.go_to_screen("result", transition=FadeTransition())

    def quit_game(self) -> None:
        if self._clock_event:
            self._clock_event.cancel()
        if self._engine:
            self._engine.stop()
        App.get_running_app().go_to_screen("menu", direction="right")


# ═══════════════════════════════════════════════════════════════════════════════
# RESULT SCREEN
# ═══════════════════════════════════════════════════════════════════════════════

class ResultScreen(BaseScreen):
    def on_enter(self, *args) -> None:
        app = App.get_running_app()
        r = app.last_result
        if not r:
            return

        mode = r.get("mode", "sprint")
        if mode == "ghost":
            won = r.get("ghost_won", False)
            gname = r.get("ghost_name", "Ghost")
            gwords = r.get("ghost_words", 0)
            if won:
                self.ids.result_title_label.text = f"You Beat {gname}!"
                self.ids.result_title_label.color = (1, 0.84, 0, 1)
            else:
                self.ids.result_title_label.text = f"So close! {gwords - r['words']} words behind"
                self.ids.result_title_label.color = (0.75, 0.4, 1, 1)
        else:
            self.ids.result_title_label.text = "Race Complete!"
            self.ids.result_title_label.color = (1, 0.84, 0, 1)

        self.ids.res_words_label.text    = str(r.get("words", 0))
        self.ids.res_wpm_label.text      = f"{r.get('wpm', 0):.1f}"
        self.ids.res_accuracy_label.text = f"{r.get('accuracy', 0):.1f}%"
        self.ids.res_score_label.text    = str(r.get("score", 0))
        self.ids.res_tier_label.text     = r.get("tier", "---")

        tier = app.rank_manager.current_tier
        self.ids.res_rank_label.text = f"Current Rank: {tier['emoji']} {tier['name']}"

        if r.get("ghost"):
            self.ids.res_ghost_save_label.text = "Ghost recorded — save it to race again!"
        else:
            self.ids.save_ghost_btn.opacity = 0
            self.ids.save_ghost_btn.disabled = True

    def save_ghost(self) -> None:
        app = App.get_running_app()
        ghost = app.last_result.get("ghost")
        if ghost:
            app.ghost_manager.save_ghost(ghost)
            self.ids.res_ghost_save_label.text = "Ghost saved!"
            self.ids.save_ghost_btn.disabled = True
            self.show_toast("Ghost saved successfully!", (0.75, 0.4, 1, 1))

    def play_again(self) -> None:
        app = App.get_running_app()
        mode = (app.last_result or {}).get("mode", "sprint")
        if mode == "ghost":
            app.go_to_screen("ghost_hub")
        else:
            app.prepare_solo_game(mode)
            app.go_to_screen("solo_game")

    def go_menu(self) -> None:
        App.get_running_app().go_to_screen("menu", direction="right")


# ═══════════════════════════════════════════════════════════════════════════════
# MULTIPLAYER RESULT SCREEN
# ═══════════════════════════════════════════════════════════════════════════════

class MultiplayerResultScreen(BaseScreen):
    def on_enter(self, *args) -> None:
        app = App.get_running_app()
        scores = getattr(app, "last_mp_result", {}).get("scores", [])

        container = self.ids.podium_container
        container.clear_widgets()
        for i, s in enumerate(scores):
            medals = ["1st", "2nd", "3rd", "4th"]
            col = BoxLayout(orientation="vertical", spacing=dp(4))
            col.add_widget(Label(text=medals[min(i, 3)], font_size=sp(20), bold=True))
            col.add_widget(Label(text=s.get("name", "?")[:8], font_size=sp(13), bold=True,
                                 color=(0, 0.85, 1, 1) if s.get("is_me") else (1, 1, 1, 1)))
            col.add_widget(Label(text=str(s.get("score", 0)), font_size=sp(15), color=(1, 0.84, 0, 1)))
            col.add_widget(Label(text=f"{s.get('accuracy', 0):.0f}% acc", font_size=sp(11),
                                 color=(0, 0.78, 0.33, 1)))
            container.add_widget(col)

        if scores and scores[0].get("is_me"):
            self.ids.mp_result_title.text = "You Won!"
            self.ids.mp_result_title.color = (1, 0.84, 0, 1)
            app.sound_manager.victory()
            app.rank_manager.record_mp_result(won=True, is_host=app.network_manager.is_host)
        else:
            self.ids.mp_result_title.text = "Race Finished!"
            self.ids.mp_result_title.color = (0.8, 0.8, 0.8, 1)
            app.rank_manager.record_mp_result(won=False, is_host=app.network_manager.is_host)

    def rematch(self) -> None:
        App.get_running_app().go_to_screen("mp_hub")

    def new_race(self) -> None:
        App.get_running_app().go_to_screen("mp_hub")

    def go_menu(self) -> None:
        App.get_running_app().go_to_screen("menu", direction="right")


# ═══════════════════════════════════════════════════════════════════════════════
# LEAGUE RANK SCREEN
# ═══════════════════════════════════════════════════════════════════════════════

class LeagueRankScreen(BaseScreen):
    def on_enter(self, *args) -> None:
        app = App.get_running_app()
        rm = app.rank_manager
        tier = rm.current_tier

        self.ids.current_tier_label.text = f"{tier['emoji']} {tier['name']}"
        self.ids.avg_wpm_label.text = f"Avg WPM (last 10): {rm.avg_wpm}"
        self.ids.avg_acc_label.text = f"Avg Accuracy: {rm.avg_accuracy:.1f}%"

        current_idx = next((i for i, t in enumerate(TIER_CONFIG) if t["name"] == tier["name"]), 0)
        if current_idx < len(TIER_CONFIG) - 1:
            nt = TIER_CONFIG[current_idx + 1]
            self.ids.next_tier_label.text = (
                f"Next: {nt['emoji']} {nt['name']} — {nt['min_wpm']}+ WPM, {nt['min_acc']}%+ acc"
            )
        else:
            self.ids.next_tier_label.text = "Maximum rank achieved!"

        container = self.ids.tier_requirements_container
        container.clear_widgets()
        for tc in TIER_CONFIG:
            row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(10))
            row.add_widget(Label(text=f"{tc['emoji']} {tc['name']}", font_size=sp(15),
                                 bold=True, color=tc["color"], size_hint_x=0.3))
            row.add_widget(Label(text=f"{tc['min_wpm']}+ WPM", font_size=sp(13),
                                 color=(0.8, 0.8, 0.8, 1), size_hint_x=0.3))
            row.add_widget(Label(text=f"{tc['min_acc']}%+ acc", font_size=sp(13),
                                 color=(0, 0.78, 0.33, 1), size_hint_x=0.4))
            container.add_widget(row)


# ═══════════════════════════════════════════════════════════════════════════════
# STATS SCREEN
# ═══════════════════════════════════════════════════════════════════════════════

class StatsScreen(BaseScreen):
    def on_enter(self, *args) -> None:
        app = App.get_running_app()
        s = app.rank_manager.stats
        self.ids.stat_best_wpm.text    = f"{s.get('best_wpm', 0):.1f}"
        self.ids.stat_avg_wpm.text     = f"{app.rank_manager.avg_wpm}"
        self.ids.stat_total_words.text = str(s.get("total_words", 0))
        self.ids.stat_best_acc.text    = f"{s.get('best_accuracy', 0):.1f}%"
        self.ids.stat_games.text       = str(s.get("games_played", 0))
        self.ids.stat_mp_wins.text     = str(s.get("mp_wins", 0))

        container = self.ids.achievements_container
        container.clear_widgets()
        unlocked_ids = {a["id"] for a in app.rank_manager.unlocked_achievements}
        for a in ACHIEVEMENTS:
            is_unlocked = a["id"] in unlocked_ids
            row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
            row.add_widget(Label(text=a["emoji"], font_size=sp(22), size_hint_x=0.12,
                                 color=(1, 1, 1, 1) if is_unlocked else (0.3, 0.3, 0.3, 1)))
            box = BoxLayout(orientation="vertical")
            box.add_widget(Label(text=a["title"], font_size=sp(14), bold=True,
                                 color=(1, 0.84, 0, 1) if is_unlocked else (0.35, 0.35, 0.35, 1),
                                 halign="left", text_size=(None, None)))
            box.add_widget(Label(text=a["desc"], font_size=sp(11),
                                 color=(0.7, 0.7, 0.7, 1) if is_unlocked else (0.3, 0.3, 0.3, 1),
                                 halign="left", text_size=(None, None)))
            row.add_widget(box)
            container.add_widget(row)


# ═══════════════════════════════════════════════════════════════════════════════
# SETTINGS SCREEN
# ═══════════════════════════════════════════════════════════════════════════════

class SettingsScreen(BaseScreen):
    def on_enter(self, *args) -> None:
        app = App.get_running_app()
        s = app.settings
        self.ids.sound_switch.active     = s.get("sound_enabled", True)
        self.ids.vibration_switch.active = s.get("vibration_enabled", True)
        self.ids.music_switch.active     = s.get("music_enabled", False)
        self.ids.player_name_input.text  = app.rank_manager.stats.get("player_name", "Player")

    def toggle_sound(self, value: bool) -> None:
        app = App.get_running_app()
        app.sound_manager.sound_enabled = value
        # Reload sounds when re-enabling
        if value:
            app.sound_manager.reload()

    def toggle_vibration(self, value: bool) -> None:
        App.get_running_app().sound_manager.vibration_enabled = value

    def toggle_music(self, value: bool) -> None:
        pass  # Future: background music

    def set_acc_feedback(self, value: str) -> None:
        App.get_running_app().settings["acc_feedback"] = value

    def update_player_name(self, value: str) -> None:
        App.get_running_app().rank_manager.stats["player_name"] = value

    def save_settings(self) -> None:
        app = App.get_running_app()
        app.settings.update({
            "sound_enabled":     self.ids.sound_switch.active,
            "vibration_enabled": self.ids.vibration_switch.active,
            "music_enabled":     self.ids.music_switch.active,
            "acc_feedback":      self.ids.acc_feedback_spinner.text,
        })
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(app.settings, f, indent=2)
        except Exception:
            pass
        app.rank_manager.save_stats()
        self.show_toast("Settings saved!", (0, 0.78, 0.33, 1))


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════════════════════════════════════════

class SpellingSprintApp(App):

    def build(self) -> ScreenManager:
        Builder.load_file("spelling_sprint.kv")

        self.rank_manager   = RankManager()
        self.sound_manager  = SoundManager()
        self.ghost_manager  = GhostManager()
        self.network_manager = NetworkManager(on_event=self._on_network_event)
        self.settings       = self._load_settings()

        # Apply saved sound settings
        self.sound_manager.sound_enabled     = self.settings.get("sound_enabled", True)
        self.sound_manager.vibration_enabled = self.settings.get("vibration_enabled", True)

        self.active_engine:    Optional[GameEngine]      = None
        self.active_ghost:     Optional[GhostRecording]  = None
        self.ghost_playback:   Optional[GhostPlayback]   = None
        self.last_result:      Optional[Dict]            = None
        self.last_mp_result:   Optional[Dict]            = None
        self.mp_game_mode:     str                       = "word"

        sm = ScreenManager()
        sm.add_widget(SplashScreen(name="splash"))
        sm.add_widget(MenuScreen(name="menu"))
        sm.add_widget(SoloGameScreen(name="solo_game"))
        sm.add_widget(LocalMultiplayerHubScreen(name="mp_hub"))
        sm.add_widget(LocalMultiplayerGameScreen(name="mp_game"))
        sm.add_widget(GhostRaceHubScreen(name="ghost_hub"))
        sm.add_widget(GhostRaceGameScreen(name="ghost_game"))
        sm.add_widget(ResultScreen(name="result"))
        sm.add_widget(MultiplayerResultScreen(name="mp_result"))
        sm.add_widget(LeagueRankScreen(name="league_rank"))
        sm.add_widget(StatsScreen(name="stats"))
        sm.add_widget(SettingsScreen(name="settings"))

        sm.current = "splash"
        return sm

    def go_to_screen(self, name: str, direction: str = "left", transition=None) -> None:
        sm = self.root
        sm.transition = transition if transition else SlideTransition(direction=direction)
        sm.current = name

    def prepare_solo_game(self, mode: str = "sprint") -> None:
        tier = self.rank_manager.word_difficulty_tier
        duration = 99999 if mode == "practice" else SPRINT_DURATION
        self.active_engine = GameEngine(duration=duration, mode=mode, tier=tier)

    def _on_network_event(self, msg: Dict) -> None:
        current = self.root.current
        screen = self.root.get_screen(current)
        handler = getattr(screen, "_on_network_event", None)
        if callable(handler):
            Clock.schedule_once(lambda dt: handler(msg), 0)

    def _load_settings(self) -> Dict:
        defaults = {
            "sound_enabled": True,
            "vibration_enabled": True,
            "music_enabled": False,
            "acc_feedback": "Normal",
        }
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    defaults.update(json.load(f))
            except Exception:
                pass
        return defaults

    def on_stop(self) -> None:
        self.network_manager.disconnect()
        self.rank_manager.save_stats()


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    SpellingSprintApp().run()