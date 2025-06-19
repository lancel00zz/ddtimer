# Facilitator Timer App

A lightweight, fullscreen-ready web app for trainers and facilitators to manage live session timers, track participant readiness, and support QR-driven check-ins.

---

**🌐 Hosted versions:**  
▶️ [https://facilitator-timer-app.onrender.com](https://facilitator-timer-app.onrender.com)  
▶️ [https://facilitator-timer-app-production.up.railway.app](https://facilitator-timer-app-production.up.railway.app)

> ⚠️ This app is designed to run in the cloud. QR check-in will **not work** if hosted locally unless all participants are on the same network (e.g., in-room Wi-Fi).

---

## Features

- ⏱ Countdown timer with Start / Stop / Reset controls
- 🔴 Red and 🟢 Green team dots to visually track team progress
- 📷 QR-code-based check-in with mobile-friendly confirmation screen (`/done`)
- ⚙️ **Configuration panel** to control appearance and behavior:
  - Font family (including Google Fonts), font color
  - Background color or image
  - Dot size (S / M / L / XL) with real-time scaling
  - Reset to defaults or edit raw JSON
- 📱 Fully responsive layout:
  - Automatically adapts to any window size
  - Shrinking the window enters **timer-only mode**, hiding team dots
- 🔁 Timer and dots persist during config updates — no resets unless requested
- 🧪 Set timer to `-1` to trigger flashing red timeout immediately (for testing)

---

## 🚀 What's New in Version 4.0

- 🧠 **Session-aware timer logic**: multiple independent sessions (from multiple trainers) can now run in parallel
- ✍️ Manually define a session ID (eg `PatrickLab1`) or let the system generate a random one
- 🔗 QR codes are now session-specific — dots and settings are scoped per session
- 🔄 Refreshing or switching sessions automatically loads the correct background, font, and config
- ❗️New “Danger Zone” section in the Config panel to clear all sessions (with password prompt)
- 🔐 Persistent settings per session stored in Flask memory — clean and fast
- 👁‍🗨 Embedded QR code and pop-up now reflect the correct session and IP-based access path
- 🧼 Improved session switching and isolation across multiple browser tabs

---
## What's New in Version 3.2.1

- 📗 info link at the bottom of the app that takes to Github public repo readme.md


## What's New in Version 3.2

- ✅ Dot size is now configurable from the config panel (S → XL)
- 🎨 Background color or image now toggle cleanly with visual confirmation
- 🖍 Font customization includes Google Fonts (Roboto, Lato, Oswald, Playfair Display)
- 🧠 "Set" dialog pre-fills with the current timer and team count
- 🛠 New "Reset All Configurations" button restores a clean, default look
- 🔴 Flashing red timer always overrides font color for visibility
- 📱 App behavior improvements and bugs fixes

---

## Docker (for development/testing only)

Running locally disables QR check-in unless everyone is on the same network. Use hosted versions in real settings.

	docker pull lancel00zz/facilitator-timer-app:3.2
	docker run -p 5056:5000 lancel00zz/facilitator-timer-app:3.2

---

## Author

Made with 💜 by Patrick Zakher  
Feel free to fork or contribute.
