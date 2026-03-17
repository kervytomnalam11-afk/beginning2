"""
network_manager.py - Local WiFi P2P networking for Spelling Sprint League.
Uses TCP for reliable game data, UDP broadcast for host discovery.
No internet required.
"""

import json
import socket
import threading
import time
from enum import Enum
from typing import Callable, Dict, List, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TCP_PORT = 5555
UDP_PORT = 5556
BROADCAST_INTERVAL = 1.0          # seconds between host announcements
DISCOVERY_TIMEOUT = 5.0           # seconds to wait for hosts
RECONNECT_ATTEMPTS = 3
RECONNECT_DELAY = 5.0 / RECONNECT_ATTEMPTS
PROGRESS_INTERVAL = 0.5           # seconds between progress broadcasts
MAX_PLAYERS = 4
BUFFER_SIZE = 4096
MAGIC = "SPELLING_SPRINT_HOST"


class Role(Enum):
    NONE = "none"
    HOST = "host"
    CLIENT = "client"


class MsgType:
    ANNOUNCE = "announce"
    PLAYER_JOIN = "player_join"
    PLAYER_LIST = "player_list"
    GAME_TYPE = "game_type"
    GAME_START = "game_start"
    WORD_SYNC = "word_sync"
    SENTENCE_SYNC = "sentence_sync"
    PROGRESS = "progress"
    ACCURACY_UPDATE = "accuracy_update"
    GAME_END = "game_end"
    PLAYER_DISCONNECT = "player_disconnect"
    PING = "ping"
    PONG = "pong"
    CHAT = "chat"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _encode(msg: dict) -> bytes:
    return (json.dumps(msg) + "\n").encode("utf-8")


def _get_local_ip() -> str:
    """Return local network IP (best-effort)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# ---------------------------------------------------------------------------
# NetworkManager
# ---------------------------------------------------------------------------

class NetworkManager:
    """
    Manages all local WiFi multiplayer networking.
    Thread-safe callbacks are delivered via the provided `on_event` handler,
    which should schedule UI updates via Kivy's Clock.schedule_once.
    """

    def __init__(self, on_event: Callable[[dict], None]) -> None:
        self.on_event = on_event
        self.role: Role = Role.NONE
        self.local_ip: str = _get_local_ip()
        self.device_name: str = socket.gethostname()[:12]

        # Host-side state
        self._clients: Dict[str, socket.socket] = {}   # player_id → socket
        self._client_lock: threading.Lock = threading.Lock()
        self._server_sock: Optional[socket.socket] = None

        # Client-side state
        self._host_sock: Optional[socket.socket] = None
        self._host_ip: Optional[str] = None
        self._player_id: Optional[str] = None

        # Shared
        self._broadcast_sock: Optional[socket.socket] = None
        self._running: bool = False
        self._game_mode: str = "word"   # "word" | "sentence"
        self._current_word: str = ""
        self._threads: List[threading.Thread] = []

    # ── Public API ─────────────────────────────────────────────────────────

    @property
    def is_connected(self) -> bool:
        return self.role != Role.NONE and self._running

    @property
    def is_host(self) -> bool:
        return self.role == Role.HOST

    def host_game(self, game_mode: str = "word") -> None:
        """Start hosting a game on the local network."""
        self._game_mode = game_mode
        self.role = Role.HOST
        self._running = True
        self._start_tcp_server()
        self._start_udp_broadcast()

    def discover_hosts(self, timeout: float = DISCOVERY_TIMEOUT) -> List[dict]:
        """
        Listen for UDP announcements and return a list of discovered hosts.
        Blocks for `timeout` seconds.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", UDP_PORT))
        sock.settimeout(timeout)
        hosts = {}
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                data, addr = sock.recvfrom(BUFFER_SIZE)
                msg = json.loads(data.decode("utf-8"))
                if msg.get("magic") == MAGIC:
                    host_ip = addr[0]
                    if host_ip not in hosts:
                        hosts[host_ip] = {
                            "ip": host_ip,
                            "name": msg.get("host_name", "Unknown"),
                            "game_mode": msg.get("game_mode", "word"),
                            "player_count": msg.get("player_count", 1),
                        }
            except socket.timeout:
                break
            except Exception:
                pass
        sock.close()
        return list(hosts.values())

    def join_game(self, host_ip: str) -> bool:
        """
        Connect to a host. Returns True on success.
        Registers this device as a client.
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((host_ip, TCP_PORT))
            sock.settimeout(None)
            self._host_sock = sock
            self._host_ip = host_ip
            self.role = Role.CLIENT
            self._running = True

            # Send join request
            self._send_to_host({
                "type": MsgType.PLAYER_JOIN,
                "name": self.device_name,
                "ip": self.local_ip,
            })

            # Start listener thread
            t = threading.Thread(target=self._client_listener, daemon=True)
            t.start()
            self._threads.append(t)
            return True
        except Exception as exc:
            print(f"[NetworkManager] join_game failed: {exc}")
            self.role = Role.NONE
            return False

    def send_progress(
        self,
        words_done: int,
        score: int,
        accuracy_pct: float,
        chars_done: int = 0,
    ) -> None:
        """Broadcast this player's current progress (called every 500 ms)."""
        msg = {
            "type": MsgType.PROGRESS,
            "player_id": self._player_id or self.local_ip,
            "words_done": words_done,
            "score": score,
            "accuracy_pct": round(accuracy_pct, 1),
            "chars_done": chars_done,
        }
        if self.role == Role.HOST:
            self._broadcast_to_clients(msg)
        elif self.role == Role.CLIENT:
            self._send_to_host(msg)

    def host_start_race(
        self,
        word_list: List[str],
        sentence_ids: Optional[List[str]] = None,
    ) -> None:
        """
        Host broadcasts the word/sentence list and triggers race start.
        Clients receive a GAME_START message with the shared word list.
        """
        msg: dict = {
            "type": MsgType.GAME_START,
            "game_mode": self._game_mode,
            "countdown": 3,
        }
        if self._game_mode == "sentence":
            msg["sentence_ids"] = sentence_ids or []
        else:
            msg["word_list"] = word_list

        self._broadcast_to_clients(msg)

    def host_sync_word(self, word: str, word_index: int) -> None:
        """Sync the current target word to all clients (Word Race)."""
        self._broadcast_to_clients({
            "type": MsgType.WORD_SYNC,
            "word": word,
            "index": word_index,
        })

    def host_sync_sentence(self, sentence_id: str, sentence_index: int) -> None:
        """Sync the current sentence to all clients (Sentence Race)."""
        self._broadcast_to_clients({
            "type": MsgType.SENTENCE_SYNC,
            "sentence_id": sentence_id,
            "index": sentence_index,
        })

    def send_game_end(self, final_scores: List[dict]) -> None:
        """Host broadcasts final scores at end of race."""
        self._broadcast_to_clients({
            "type": MsgType.GAME_END,
            "scores": final_scores,
        })

    def disconnect(self) -> None:
        """Cleanly disconnect from any active session."""
        self._running = False
        if self._server_sock:
            try:
                self._server_sock.close()
            except Exception:
                pass
        if self._host_sock:
            try:
                self._host_sock.close()
            except Exception:
                pass
        if self._broadcast_sock:
            try:
                self._broadcast_sock.close()
            except Exception:
                pass
        with self._client_lock:
            for sock in self._clients.values():
                try:
                    sock.close()
                except Exception:
                    pass
            self._clients.clear()
        self.role = Role.NONE

    # ── Host internals ─────────────────────────────────────────────────────

    def _start_tcp_server(self) -> None:
        """Open a TCP server socket and start accepting clients."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", TCP_PORT))
        sock.listen(MAX_PLAYERS - 1)
        sock.settimeout(1.0)
        self._server_sock = sock

        t = threading.Thread(target=self._accept_clients, daemon=True)
        t.start()
        self._threads.append(t)

    def _accept_clients(self) -> None:
        """Accept incoming client connections."""
        while self._running:
            try:
                client_sock, addr = self._server_sock.accept()
                pid = addr[0]
                with self._client_lock:
                    if len(self._clients) < MAX_PLAYERS - 1:
                        self._clients[pid] = client_sock
                # Listen for this client's messages
                t = threading.Thread(
                    target=self._host_client_listener,
                    args=(pid, client_sock),
                    daemon=True,
                )
                t.start()
                self._threads.append(t)
            except socket.timeout:
                continue
            except Exception:
                break

    def _host_client_listener(self, player_id: str, sock: socket.socket) -> None:
        """Listen for messages from a specific client (host side)."""
        buf = ""
        while self._running:
            try:
                data = sock.recv(BUFFER_SIZE)
                if not data:
                    self._handle_disconnect(player_id)
                    break
                buf += data.decode("utf-8")
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    if line:
                        msg = json.loads(line)
                        msg["_sender_id"] = player_id
                        # Forward progress updates to all other clients
                        if msg.get("type") == MsgType.PROGRESS:
                            self._broadcast_to_clients(msg, exclude=player_id)
                        self._deliver(msg)
            except Exception:
                self._handle_disconnect(player_id)
                break

    def _start_udp_broadcast(self) -> None:
        """Repeatedly broadcast UDP announcements so clients can discover this host."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self._broadcast_sock = sock

        def _broadcast_loop() -> None:
            while self._running:
                with self._client_lock:
                    pc = len(self._clients) + 1
                msg = json.dumps({
                    "magic": MAGIC,
                    "host_name": self.device_name,
                    "host_ip": self.local_ip,
                    "game_mode": self._game_mode,
                    "player_count": pc,
                })
                try:
                    sock.sendto(msg.encode("utf-8"), ("<broadcast>", UDP_PORT))
                except Exception:
                    pass
                time.sleep(BROADCAST_INTERVAL)

        t = threading.Thread(target=_broadcast_loop, daemon=True)
        t.start()
        self._threads.append(t)

    def _broadcast_to_clients(self, msg: dict, exclude: Optional[str] = None) -> None:
        payload = _encode(msg)
        with self._client_lock:
            for pid, sock in list(self._clients.items()):
                if pid == exclude:
                    continue
                try:
                    sock.sendall(payload)
                except Exception:
                    self._handle_disconnect(pid)

    def _handle_disconnect(self, player_id: str) -> None:
        with self._client_lock:
            sock = self._clients.pop(player_id, None)
        if sock:
            try:
                sock.close()
            except Exception:
                pass
        self._deliver({"type": MsgType.PLAYER_DISCONNECT, "player_id": player_id})

    # ── Client internals ───────────────────────────────────────────────────

    def _client_listener(self) -> None:
        """Listen for messages from the host (client side)."""
        buf = ""
        attempt = 0
        while self._running:
            try:
                data = self._host_sock.recv(BUFFER_SIZE)
                if not data:
                    raise ConnectionError("Host closed connection")
                buf += data.decode("utf-8")
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    if line:
                        self._deliver(json.loads(line))
                attempt = 0  # Reset reconnect counter on success
            except Exception:
                if not self._running:
                    break
                attempt += 1
                if attempt <= RECONNECT_ATTEMPTS:
                    time.sleep(RECONNECT_DELAY)
                    # Try to reconnect
                    if self._host_ip and self._reconnect():
                        continue
                self._deliver({"type": MsgType.PLAYER_DISCONNECT, "player_id": "host"})
                self._running = False
                break

    def _send_to_host(self, msg: dict) -> None:
        if self._host_sock:
            try:
                self._host_sock.sendall(_encode(msg))
            except Exception:
                pass

    def _reconnect(self) -> bool:
        """Attempt to re-establish connection to host."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((self._host_ip, TCP_PORT))
            sock.settimeout(None)
            self._host_sock = sock
            self._send_to_host({
                "type": MsgType.PLAYER_JOIN,
                "name": self.device_name,
                "ip": self.local_ip,
                "reconnect": True,
            })
            return True
        except Exception:
            return False

    # ── Deliver event to app ───────────────────────────────────────────────

    def _deliver(self, msg: dict) -> None:
        """Deliver a network event to the app's on_event handler (thread-safe)."""
        try:
            self.on_event(msg)
        except Exception as exc:
            print(f"[NetworkManager] on_event error: {exc}")

    # ── Utility ────────────────────────────────────────────────────────────

    def get_local_ip(self) -> str:
        return self.local_ip

    def get_client_count(self) -> int:
        with self._client_lock:
            return len(self._clients)
