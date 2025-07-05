# app/routes.py
import io
import os
import json
import qrcode
import time

# ── helper to load default UI from config/config.json at every startup ──
from pathlib import Path

def _load_default_from_file() -> dict:
    cfg_path = Path("config/config.json")
    try:
        with cfg_path.open() as f:
            return json.load(f)
    except Exception as exc:
        # Fallback to hard‑coded sane defaults if file missing / bad
        print(f"[facilitator‑timer] Could not read {cfg_path}: {exc}")
        return {
            "ui": {
                "background_color": "#b36ab4",
                "font_family": "Oswald",
                "font_color": "#000000",
                "dot_size": "M",
                "background_image": None
            }
        }
import random
import string

from flask import (
    Blueprint,
    render_template,
    request,
    send_file,
    jsonify,
    abort
)
from werkzeug.utils import secure_filename

from collections import defaultdict
from datetime import datetime
from threading import Lock

session_configs = defaultdict(lambda: _load_default_from_file())

# In-memory session-scoped tracking for /done, /ping, /reset
sessions = defaultdict(lambda: {"count": 0, "last_ping": datetime.now()})

# 1) Define a Blueprint called "main"
main = Blueprint("main", __name__)

# Admin‑only one‑shot flag that allows an intentional write on “default”
# ─────────────────────────────────────────────────────────────
ADMIN_CLEAR_PASSWORD = "3.1415!"   # reuse same password


# ───────────────────────────────────────────────────────────────────────
@main.route("/")
def home():
    """
    The main timer page. Renders popup.html.
    """
    return render_template("popup.html")


@main.route("/settings")
def settings():
    """
    Renders the Settings page (settings.html).
    """
    return render_template("settings.html")


@main.route("/edit-config", methods=["GET", "POST"])
def edit_config():
    """
    GET  → Load config/session_states.json, pretty-print the session's state inside edit-config.html.
    POST → Read the JSON from the textarea and overwrite the session's state in session_states.json.
    """
    if request.method == "POST":
        session_id = request.args.get("session", "default")

        raw_json = request.form.get("config_json", "").strip()
        try:
            parsed = json.loads(raw_json)
        except Exception as e:
            return f"<h1>Invalid JSON</h1><p>{e}</p>", 400

        # Load all session states
        all_states = _load_all_session_states()
        all_states[session_id] = parsed
        _save_all_session_states(all_states)

        # Respond with JSON so the fetch() in edit‑config.html can act on it
        return jsonify({"new_session": None}), 200

    # ─────────────────── If GET → render form with current JSON ───────────────────
    session_id = request.args.get("session", "default")
    all_states = _load_all_session_states()
    content = all_states.get(session_id)
    if content is None:
        # fallback to config.json's UI section, but as a full dict
        content = _load_default_from_file()
    pretty = json.dumps(content, indent=2)

    return render_template(
        "edit-config.html",
        config_content=pretty
    )


# ───────────────────────────────────────────────────────────────────────

SESSION_STATE_FILE = Path("config/session_states.json")
session_state_lock = Lock()

def _load_all_session_states():
    if not SESSION_STATE_FILE.exists():
        return {}
    try:
        with SESSION_STATE_FILE.open("r") as f:
            return json.load(f)
    except Exception as exc:
        print(f"[facilitator-timer] Could not read {SESSION_STATE_FILE}: {exc}")
        return {}

def _save_all_session_states(states):
    try:
        with session_state_lock:
            with SESSION_STATE_FILE.open("w") as f:
                json.dump(states, f, indent=2)
    except Exception as exc:
        print(f"[facilitator-timer] Could not write {SESSION_STATE_FILE}: {exc}")

@main.route("/api/session-state", methods=["GET", "POST"])
def api_session_state():
    session_id = request.args.get("session", "default")
    if request.method == "GET":
        all_states = _load_all_session_states()
        state = all_states.get(session_id, {})
        return jsonify(state)
    elif request.method == "POST":
        try:
            data = request.get_json(force=True)
        except Exception as e:
            return jsonify({"error": f"Invalid JSON: {e}"}), 400
        all_states = _load_all_session_states()
        all_states[session_id] = data
        _save_all_session_states(all_states)
        return jsonify({"ok": True})


@main.route("/done")
def done():
    """
    Called by the QR scanner. Increments scan count for the session and returns a confirmation string.
    """
    session_id = request.args.get("session", "default")
    sessions[session_id]["count"] += 1
    sessions[session_id]["last_ping"] = datetime.now()
    return """
<html>
  <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
      body {
        font-family: sans-serif;
        font-size: 2.5rem;
        text-align: center;
        padding: 2em;
      }
    </style>
  </head>
  <body>
    ✅ Submission received!<br><br>
    You may return to your team.
  </body>
</html>
"""


@main.route("/ping")
def ping():
    """
    Called periodically by the frontend (every 2 seconds). Returns the current session scan count.
    """
    session_id = request.args.get("session", "default")
    return str(sessions[session_id]["count"])


@main.route("/reset", methods=["POST"])
def reset():
    """
    Resets the scan count for the session back to zero. Called when the facilitator resets the dots.
    """
    session_id = request.args.get("session", "default")
    sessions[session_id]["count"] = 0
    sessions[session_id]["last_ping"] = datetime.now()
    return "OK"


@main.route("/qr-popup")
def qr_popup():
    """
    Renders a standalone page showing the same QR code (in a larger popup).
    """
    return render_template("qr_popup.html")


@main.route("/view-config")
def view_config():
    """
    Returns the raw JSON (pretty-printed) so a user can inspect it.
    """
    try:
        cfg_path = os.path.join("config", "config.json")
        with open(cfg_path, "r") as f:
            content = json.load(f)
            pretty = json.dumps(content, indent=2)
            return pretty, 200, {"Content-Type": "application/json"}
    except Exception as e:
        return f"Error loading config: {e}", 500


@main.route("/api/config")
def api_config():
    """
    Returns the current session's UI config from memory.
    """
    session_id = request.args.get("session", "default")
    return jsonify(session_configs[session_id])


# ───────────────────────────────────────────────────────────────────────

@main.route("/qr-image")
def qr_image():
    """
    Dynamically generate a PNG QR code that encodes the URL of /done.
    When a phone scans this QR, it will open https://<host>/done and register a check-in.
    """
    # Build the full /done URL dynamically using request.url_root
    session_id = request.args.get("session")
    base = request.url_root.rstrip('/')
    done_url = f"{base}/done"
    if session_id:
        done_url += f"?session={session_id}"

    img = qrcode.make(done_url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return send_file(buf, mimetype="image/png")


# ───────────────────────────────────────────────────────────────────────
# Endpoint to clear all sessions and configs (admin-only operation)
@main.route("/upload-background", methods=["POST"])
def upload_background():
    session = request.args.get("session", "default")
    
    if "bg_file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files["bg_file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    
    if file:
        # Create a unique filename based on session and original filename
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        unique_filename = f"{session}_{name}_{int(time.time())}{ext}"
        
        # Save to static directory
        static_dir = Path("app/static")
        static_dir.mkdir(exist_ok=True)
        file_path = static_dir / unique_filename
        
        try:
            file.save(str(file_path))
            return jsonify({"filename": unique_filename})
        except Exception as e:
            return jsonify({"error": f"Failed to save file: {str(e)}"}), 500
    
    return jsonify({"error": "Invalid file"}), 400