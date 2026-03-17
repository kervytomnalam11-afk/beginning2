[app]

# ─── Identity ────────────────────────────────────────────────────────────────
title = Spelling Sprint League
package.name = spellingsprint
package.domain = org.nalam
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,gz
version = 1.0

# ─── Entry point ─────────────────────────────────────────────────────────────
source.main = main.py

# ─── Requirements ─────────────────────────────────────────────────────────────
# Core: python3, kivy 2.1, kivymd for extra widgets
# Optional: qrcode for QR ghost sharing, pillow required by qrcode
requirements = python3,kivy==2.1.0,kivymd,pillow,qrcode,zxing-cpp

# ─── Display ─────────────────────────────────────────────────────────────────
orientation = portrait
fullscreen = 0
android.wakelock = False

# ─── Icons / Splash ───────────────────────────────────────────────────────────
# Replace these paths with actual 512x512 PNG assets before building
icon.filename = %(source.dir)s/assets/ic_launcher.png
presplash.filename = %(source.dir)s/assets/presplash.png

# Presplash colour while KV loads (dark navy)
android.presplash_color = #0A1628

# ─── Permissions ─────────────────────────────────────────────────────────────
android.permissions = VIBRATE,INTERNET,ACCESS_WIFI_STATE,ACCESS_NETWORK_STATE,CHANGE_WIFI_MULTICAST_STATE,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE

# ─── Android SDK / NDK ───────────────────────────────────────────────────────
android.api = 33
android.minapi = 26
android.ndk = 25c
android.sdk = 33
android.ndk_api = 21

# Use latest python-for-android
p4a.branch = master

# ─── Build settings ───────────────────────────────────────────────────────────
android.archs = arm64-v8a, armeabi-v7a
android.release_artifact = apk
# Target APK under 60 MB — strip unused libs
android.add_aars =
android.gradle_dependencies =

# ─── App store metadata ───────────────────────────────────────────────────────
android.add_activity_launch_intent = True
# android.keystore = /path/to/your.keystore   # uncomment for signed release builds
# android.keystore_alias = spellingsprint

# ─── Logging ─────────────────────────────────────────────────────────────────
log_level = 2

# ─── Bootstrap ───────────────────────────────────────────────────────────────
p4a.bootstrap = sdl2

# ─────────────────────────────────────────────────────────────────────────────
[buildozer]
# Build output directory
build_dir = ./.buildozer
# Compiled APK output directory
bin_dir = ./bin

# Set to 1 to enable verbose build output
log_level = 2

# Warn only: set to 1 to treat warnings as errors
warn_on_root = 1
