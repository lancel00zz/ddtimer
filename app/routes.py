# app/routes.py
from flask import (
    Blueprint,
    render_template,
    request,
    send_file,
    jsonify,
    redirect,
    url_for,
    Response
)
import qrcode
import io
import os
import json
from werkzeug.utils import secure_filename

main = Blueprint("main", __name__)


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
            # Store the chosen color in JSON
            parsed["ui"]["background_color"] = picked_color
            # If user chose a color, clear any existing image preference
            parsed["ui"]["background_image"] = None

        # Write the JSON back (now including any color changes)
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
                # (and clear out background_color since an image now takes priority)
                try:
                    parsed["ui"]["background_image"] = filename
                    parsed["ui"]["background_color"] = None
                    with open(config_path, "w") as f:
                        json.dump(parsed, f, indent=2)
                except Exception as cfg_err:
                    return f"<h1>Failed to update config.json</h1><p>{cfg_err}</p>", 500

        # ── 4) Reload parent timer and close this popup ──
        return """
        <script>
          // 1) Reload the main timer page so it picks up new config
          window.opener.location.reload();
          // 2) Close this popup window
          window.close();
        </script>
        """

    # ─────────────────── If GET → render form with current JSON ───────────────────
    try:
        with open(config_path, "r") as f:
            content = json.load(f)
            pretty = json.dumps(content, indent=2)
    except Exception as e:
        pretty = json.dumps({"error": str(e)}, indent=2)

    # Extract the current background_color if present, otherwise default to "#d0f0ff"
    cfg_ui = content.get("ui", {}) if isinstance(content, dict) else {}
    current_color = cfg_ui.get("background_color") or "#d0f0ff"

    return render_template(
        "edit-config.html",
        config_content=pretty,
        background_color=current_color
    )

@main.route("/done")
def done():
    """
    Called by the QR scanner. Increments scan_count and returns a confirmation string.
    """
    global scan_count
    scan_count += 1
    return "✅ Submission received! You may return to your team."


@main.route("/ping")
def ping():
    """
    Called periodically by the frontend (every 2 seconds). Returns the current scan_count.
    """
    global scan_count
    return str(scan_count)


@main.route("/reset", methods=["POST"])
def reset():
    """
    Resets the scan_count back to zero. Called when the facilitator resets the dots.
    """
    global scan_count
    scan_count = 0
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
    Returns the raw JSON (pretty‐printed) so a user can inspect it.
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
    Returns the exact /config/config.json as a JSON object 
    (for “fetch()” on the frontend).
    """
    try:
        cfg_path = os.path.join("config", "config.json")
        with open(cfg_path, "r") as f:
            content = json.load(f)
            return jsonify(content)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route("/qr-image")
def qr_image():
    """
    Dynamically generate a PNG QR code that encodes the URL of our /done route.
    When a phone scans this QR, it will open https://<host>/done and register a check-in.
    """
    # 1) Build the full URL to /done (include scheme + host + port)
    #    request.url_root ends with a trailing slash, e.g. "http://localhost:5050/"
    done_url = request.url_root.rstrip("/") + "/done"

    # 2) Generate a QR image
    img = qrcode.make(done_url)

    # 3) Write it into an in-memory buffer
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    # 4) Return it as a PNG response
    return send_file(buf, mimetype="image/png")