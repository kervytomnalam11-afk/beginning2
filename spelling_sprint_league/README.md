# Spelling Sprint League 🏆⚡

> A fast-paced educational typing race game for Android with local WiFi multiplayer and ghost racing.

---

## Features

- **Sprint Mode** — 60-second timed race, spell as many words as possible
- **League Mode** — Progressive difficulty (Bronze → Diamond) based on your WPM and accuracy
- **Practice Mode** — Unlimited time, no pressure, perfect for learning
- **Local WiFi Race** — 2–4 players on the same network, no internet needed
  - **Word Race** — 60 seconds, individual words
  - **Sentence Race** — 90 seconds, full sentence passages
- **Ghost Race** — Record your runs, share them, race against them later
- **Accuracy System** — Character-level tracking, tier badges, bonuses & penalties
- **Achievements** — Unlock 11 badges across solo, multiplayer, and ghost modes

---

## Project Structure

```
spelling_sprint_league/
├── main.py              # App, all screen classes, GameEngine, RankManager, SoundManager
├── spelling_sprint.kv   # All KV UI definitions
├── network_manager.py   # Local WiFi P2P (TCP game data + UDP discovery)
├── ghost_manager.py     # Ghost recording, playback, file I/O, QR export
├── accuracy_tracker.py  # Real-time accuracy, heatmaps, tier classification
├── word_bank.py         # Word lists (Bronze → Diamond difficulty)
├── sentence_bank.py     # Sentence passages (quotes, science, history, literature)
├── buildozer.spec       # Android APK build configuration
├── assets/
│   ├── ic_launcher.png  # 512×512 app icon (add before building)
│   └── presplash.png    # Splash screen image (add before building)
└── README.md
```

---

## Build Instructions

### Prerequisites

```bash
# Ubuntu / Debian
sudo apt update && sudo apt install -y \
  python3 python3-pip git zip unzip \
  openjdk-17-jdk build-essential \
  libssl-dev libffi-dev libsqlite3-dev \
  autoconf automake libtool pkg-config

pip3 install buildozer
pip3 install kivy kivymd
```

### Desktop testing (before Android)

```bash
cd spelling_sprint_league/
pip3 install kivy kivymd pillow qrcode
python3 main.py
```

### Build Android APK

```bash
cd spelling_sprint_league/

# First build (downloads SDK/NDK — takes 20–40 min)
buildozer android debug

# Subsequent builds are faster
buildozer android debug deploy run

# Release build (requires keystore)
buildozer android release
```

The APK will be in `./bin/spellingsprint-1.0-debug.apk`.

### Install on device

```bash
adb install bin/spellingsprint-1.0-debug.apk
```

Or transfer the APK file to your Android device and install it directly.

---

## Multiplayer Setup

### Hosting a Game

1. Open **Local WiFi Race** from the main menu
2. Tap **Host Game** → choose **Word Race** or **Sentence Race**
3. Share your IP address (shown on screen) with friends
4. Wait for friends to join (up to 3 guests)
5. When ready, tap **Start Race**

### Joining a Game

1. Open **Local WiFi Race**
2. Tap **Join Game** — auto-discovery scans the local network
3. Select the host from the list, OR tap **Enter IP Manually** if auto-discovery fails
4. Wait for the host to start the race

### Network Requirements

- All players must be on the **same WiFi network**
- No internet connection required
- Ports used: TCP 5555 (game data), UDP 5556 (discovery)
- If your router blocks UDP broadcast, use **manual IP entry**

---

## Ghost Race

### Saving a Ghost

After any solo game, tap **Save as Ghost** on the results screen.
Ghosts are stored in `~/SpellingSprint/Ghosts/` on your device.

### Racing a Ghost

From the **Ghost Race** hub:
- Tap **Race Your Best** to instantly challenge your top ghost
- Or select any ghost from the list and tap **Race**

### Sharing Ghosts

1. Tap **Share** next to a ghost — it exports a `.json.gz` file to `~/SpellingSprint/`
2. Send that file to a friend via Bluetooth, email, or any file-sharing app
3. Friend places the file in `~/SpellingSprint/Ghosts/` and taps **Import Ghost**

---

## Scoring

| Event | Points |
|-------|--------|
| Word correct | 10 pts × streak multiplier |
| Speed bonus | Up to +5 pts (proportional to remaining time) |
| Perfect accuracy (100%) | +50 pts |
| Excellent accuracy (95–99%) | +25 pts |
| Good accuracy (90–94%) | +10 pts |
| Fair accuracy (80–89%) | −5% final score |
| Poor accuracy (<80%) | −10% final score |

### Streak Multipliers

| Streak | Multiplier |
|--------|-----------|
| 1–4 words | ×1.0 |
| 5–9 words | ×1.2 |
| 10–14 words | ×1.5 |
| 15+ words | ×2.0 |

---

## Rank Tiers

| Tier | WPM Requirement | Accuracy Requirement |
|------|----------------|---------------------|
| 🥉 Bronze | 0–20 WPM | none |
| 🥈 Silver | 21–35 WPM | 60%+ |
| 🥇 Gold | 36–50 WPM | 75%+ |
| 💎 Platinum | 51–70 WPM | 85%+ |
| 🔷 Diamond | 71+ WPM | 90%+ |

Tier is calculated from your **average across the last 10 solo games**.

---

## Community Ghosts (Optional)

To share ghosts publicly, host a `ghosts.json` file on any free static host:

```json
{
  "version": "1.0",
  "ghosts": [
    {
      "name": "Speed King",
      "wpm": 85.3,
      "accuracy_pct": 97.2,
      "tier": "diamond",
      "download_url": "https://your-host.github.io/ghost_abc123.json.gz"
    }
  ]
}
```

Point the app to your JSON URL by editing `GhostRaceHubScreen.browse_community_ghosts()` in `main.py`.

---

## Data Storage

All data is stored locally — no accounts, no servers required.

| File | Contents |
|------|----------|
| `~/SpellingSprint/stats.json` | Player stats, achievements, rank history |
| `~/SpellingSprint/settings.json` | App settings |
| `~/SpellingSprint/Ghosts/*.json.gz` | Ghost recordings |

---

## License

MIT License — free for personal and educational use.
