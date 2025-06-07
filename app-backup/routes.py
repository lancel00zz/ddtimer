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

# 1) Define a Blueprint called "main"
main = Blueprint("main", __name__)

# Session-based state
import uuid
session_data = {}


# ───────────────────────────────────────────────────────────────────────
@main.route("/")
def home():
    session_id = str(uuid.uuid4())[:8]
    return redirect(url_for("main.session_index", session_id=session_id))


# Session-based index page
@main.route("/session/<session_id>")
def session_index(session_id):
    if session_id not in session_data:
        session_data[session_id] = {
            "timer": None,
            "dots": [],
            "done": set()
        }
    return render_template("popup.html", session_id=session_id)


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
        # ── 1) Read & validate JSON from the <textarea> ──
        raw_json = request.form.get("config_json", "").strip()
        try:
            parsed = json.loads(raw_json)
        except Exception as e:
            return f"<h1>Invalid JSON</h1><p>{e}</p>", 400

        # Ensure "ui" key exists
        if "ui" not in parsed or not isinstance(parsed["ui"], dict):
            parsed["ui"] = {}

        # ── 2) Handle the color-picker value ──
        picked_color = request.form.get("background_color", "").strip()
        if picked_color:
            parsed["ui"]["background_color"] = picked_color
            parsed["ui"]["background_image"] = None

        try:
            with open(config_path, "w") as f:
                json.dump(parsed, f, indent=2)
        except Exception as e:
            return f"<h1>Failed to write config.json</h1><p>{e}</p>", 500

        # ── 3) Handle optional background-image upload ──
        if "bg_file" in request.files:
            file = request.files["bg_file"]
            if file and file.filename:
                filename = secure_filename(file.filename)
                save_path = os.path.join("app", "static", filename)
                try:
                    file.save(save_path)
                except Exception as save_err:
                    return f"<h1>Failed to save image</h1><p>{save_err}</p>", 500

                # Update JSON so that ui.background_image = <filename>
                parsed["ui"]["background_image"] = filename
                parsed["ui"]["background_color"] = None
                try:
                    with open(config_path, "w") as f:
                        json.dump(parsed, f, indent=2)
                except Exception as cfg_err:
                    return f"<h1>Failed to update config.json</h1><p>{cfg_err}</p>", 500

        # ── 4) Reload parent timer and close this popup ──
        return """
        <script>
          window.opener.location.reload();
          window.close();
        </script>
        """

    # ─────────────────── If GET → render form with current JSON ───────────────────
    try:
        with open(config_path, "r") as f:
            content = json.load(f)
            pretty = json.dumps(content, indent=2)
    except Exception as e:
        content = {"error": str(e)}
        pretty = json.dumps(content, indent=2)

    cfg_ui = content.get("ui", {}) if isinstance(content, dict) else {}
    current_color = cfg_ui.get("background_color") or "#d0f0ff"

    return render_template(
        "edit-config.html",
        config_content=pretty,
        background_color=current_color
    )


# ───────────────────────────────────────────────────────────────────────
@main.route("/session/<session_id>/done")
def done(session_id):
    if session_id not in session_data:
        return "Invalid session", 404
    session_data[session_id]["done"].add(request.remote_addr)
    return "✅ Submission received! You may return to your team."


@main.route("/session/<session_id>/ping")
def ping(session_id):
    if session_id not in session_data:
        return "0"
    return str(len(session_data[session_id]["done"]))


@main.route("/session/<session_id>/reset", methods=["POST"])
def reset(session_id):
    if session_id in session_data:
        session_data[session_id]["done"].clear()
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
    Returns the exact /config/config.json as a JSON object (for fetch() on the frontend).
    """
    try:
        cfg_path = os.path.join("config", "config.json")
        with open(cfg_path, "r") as f:
            content = json.load(f)
            return jsonify(content)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ───────────────────────────────────────────────────────────────────────
@main.route("/session/<session_id>/qr-image")
def qr_image(session_id):
    done_url = request.url_root.rstrip("/") + f"/session/{session_id}/done"
    img = qrcode.make(done_url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")