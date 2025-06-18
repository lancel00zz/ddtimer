# app/routes.py
import io
import os
import json
import qrcode

from flask import (
    Blueprint,
    render_template,
    request,
    send_file,
    jsonify
)
from werkzeug.utils import secure_filename

from collections import defaultdict
from datetime import datetime

session_configs = defaultdict(lambda: {
    "ui": {
        "background_color": "#b36ab4",
        "font_family": "Oswald",
        "font_color": "#000000",
        "dot_size": "M",
        "background_image": None
    }
})

# 1) Define a Blueprint called "main"
main = Blueprint("main", __name__)


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
    GET  → Load config/config.json, pretty-print its contents inside edit-config.html.
    POST → 
      1) Read the JSON from the textarea and overwrite config/config.json.
      2) Read the color-picker value (background_color) and save into JSON.
      3) If a background-image file was uploaded, save it under app/static/ and update JSON.
      4) Return a small <script> that reloads the opener window (timer) and closes this popup.
    """
    config_path = os.path.join("config", "config.json")

    if request.method == "POST":
        session_id = request.args.get("session", "default")

        raw_json = request.form.get("config_json", "").strip()
        try:
            parsed = json.loads(raw_json)
        except Exception as e:
            return f"<h1>Invalid JSON</h1><p>{e}</p>", 400

        if "ui" not in parsed or not isinstance(parsed["ui"], dict):
            parsed["ui"] = {}

        picked_color = request.form.get("background_color", "").strip()
        if picked_color:
            parsed["ui"]["background_color"] = picked_color
            parsed["ui"]["background_image"] = None

        if "bg_file" in request.files:
            file = request.files["bg_file"]
            if file and file.filename:
                filename = secure_filename(file.filename)
                save_path = os.path.join("app", "static", filename)
                try:
                    file.save(save_path)
                except Exception as save_err:
                    return f"<h1>Failed to save image</h1><p>{save_err}</p>", 500
                parsed["ui"]["background_image"] = filename
                parsed["ui"]["background_color"] = None

        session_configs[session_id] = parsed

        return f"""
        <script>
          if (window.opener && window.opener.loadAndApplyConfig) {{
            window.opener.loadAndApplyConfig(true);
          }}
          // Ensure session indicator persists
          if (window.opener && window.opener.document.getElementById('session-indicator')) {{
            window.opener.document.getElementById('session-indicator').textContent = 'Session ID: {session_id}';
          }}
          window.close();
        </script>
        """

    # ─────────────────── If GET → render form with current JSON ───────────────────
    session_id = request.args.get("session", "default")
    content = session_configs[session_id]
    pretty = json.dumps(content, indent=2)
    cfg_ui = content.get("ui", {}) if isinstance(content, dict) else {}
    current_color = cfg_ui.get("background_color") or "#d0f0ff"

    return render_template(
        "edit-config.html",
        config_content=pretty,
        background_color=current_color
    )


# ───────────────────────────────────────────────────────────────────────

# In-memory session-scoped tracking for /done, /ping, /reset
sessions = defaultdict(lambda: {"count": 0, "last_ping": datetime.now()})

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
    # Build the full /done URL based on whatever host called us (ngrok or Railway)
    session_id = request.args.get("session")
    done_url = request.url_root.rstrip("/") + "/done"
    if session_id:
        done_url += f"?session={session_id}"

    img = qrcode.make(done_url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return send_file(buf, mimetype="image/png")


# ───────────────────────────────────────────────────────────────────────
# Endpoint to clear all sessions and configs (admin-only operation)
@main.route("/clear-sessions", methods=["POST"])
def clear_sessions():
    """
    Clears all in-memory session configs and scan counts.
    """
    session_configs.clear()
    sessions.clear()
    return "OK", 200