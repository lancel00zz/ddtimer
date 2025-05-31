from flask import Blueprint, render_template, request, send_file
import qrcode
import io
import os

main = Blueprint("main", __name__)

@main.route("/")
def home():
    return render_template("popup.html")

@main.route("/settings")
def settings():
    return render_template("settings.html")

@main.route("/qr-image")
def qr_image():
    ip = get_local_ip()
    full_url = f"http://{ip}:5050/done"

    img = qrcode.make(full_url)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return send_file(buffer, mimetype='image/png')

def get_local_ip():
    return os.environ.get("HOST_IP", "127.0.0.1")

scan_count = 0

@main.route("/done")
def done():
    global scan_count
    scan_count += 1
    return "✅ Submission received! You may return to your team."

@main.route("/ping")
def ping():
    global scan_count
    return str(scan_count)

@main.route("/reset", methods=["POST"])
def reset():
    global scan_count
    scan_count = 0
    return "OK"

@main.route("/qr-popup")
def qr_popup():
    return render_template("qr_popup.html")