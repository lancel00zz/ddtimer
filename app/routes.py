# ... existing imports ...
import io
import os
import json
import qrcode
import time

from pathlib import Path
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

from .models import SessionState
from . import db

session_configs = defaultdict(lambda: _load_default_from_file())

# In-memory session-scoped tracking for /done, /ping, /reset
sessions = defaultdict(lambda: {"count": 0, "last_ping": datetime.now()})

main = Blueprint("main", __name__)

ADMIN_CLEAR_PASSWORD = "3.1415!"   # reuse same password

def _load_default_from_file() -> dict:
    return _load_golden_standard()

# --- Database-backed session state helpers ---
def get_session_state(session_id):
    record = SessionState.query.filter_by(session_id=session_id).first()
    return record.state if record else {}

def set_session_state(session_id, state):
    record = SessionState.query.filter_by(session_id=session_id).first()
    if record:
        record.state = state
    else:
        record = SessionState(session_id=session_id, state=state)
        db.session.add(record)
    db.session.commit()

# --- Routes ---

@main.route("/")
def home():
    return render_template("popup.html")

@main.route("/settings")
def settings():
    return render_template("settings.html")

@main.route("/edit-config", methods=["GET", "POST"])
def edit_config():
    if request.method == "POST":
        session_id = request.args.get("session", "default")
        raw_json = request.form.get("config_json", "").strip()
        try:
            parsed = json.loads(raw_json)
        except Exception as e:
            return f"<h1>Invalid JSON</h1><p>{e}</p>", 400
        set_session_state(session_id, parsed)
        return jsonify({"new_session": None}), 200

    session_id = request.args.get("session", "default")
    if not session_id or session_id == "default":
        content = _load_golden_standard()
    else:
        content = get_session_state(session_id)
        if content is None:
            content = _load_golden_standard()
    pretty = json.dumps(content, indent=2)
    return render_template("edit-config.html", config_content=pretty)

@main.route("/api/session-state", methods=["GET", "POST"])
def api_session_state():
    session_id = request.args.get("session", "default")
    if request.method == "GET":
        state = get_session_state(session_id)
        return jsonify(state)
    elif request.method == "POST":
        try:
            data = request.get_json(force=True)
        except Exception as e:
            return jsonify({"error": f"Invalid JSON: {e}"}), 400
        set_session_state(session_id, data)
        return jsonify({"ok": True})

@main.route("/done")
def done():
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
    session_id = request.args.get("session", "default")
    return str(sessions[session_id]["count"])

@main.route("/reset", methods=["POST"])
def reset():
    session_id = request.args.get("session", "default")
    sessions[session_id]["count"] = 0
    sessions[session_id]["last_ping"] = datetime.now()
    return "OK"

@main.route("/qr-popup")
def qr_popup():
    return render_template("qr_popup.html")

@main.route("/view-config")
def view_config():
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
    session_id = request.args.get("session", "default")
    return jsonify(session_configs[session_id])

@main.route("/qr-image")
def qr_image():
    session = request.args.get("session", "default")
    img = qrcode.make(session)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")

@main.route("/upload-background", methods=["POST"])
def upload_background():
    session = request.args.get("session", "default")
    if "bg_file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files["bg_file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    if file:
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        unique_filename = f"{session}_{name}_{int(time.time())}{ext}"
        static_dir = Path("app/static")
        static_dir.mkdir(exist_ok=True)
        file_path = static_dir / unique_filename
        try:
            file.save(str(file_path))
            return jsonify({"filename": unique_filename})
        except Exception as e:
            return jsonify({"error": f"Failed to save file: {str(e)}"}), 500
    return jsonify({"error": "Invalid file"}), 400

def _load_golden_standard() -> dict:
    gs_path = Path("config/golden_standard.json")
    try:
        with gs_path.open() as f:
            return json.load(f)
    except Exception as exc:
        print(f"[facilitator-timer] Could not read {gs_path}: {exc}")
        return {}

@main.route("/api/golden-standard", methods=["GET"])
def api_golden_standard():
    return jsonify(_load_golden_standard())