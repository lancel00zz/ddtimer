import io
import os
import json
import qrcode
import time
import traceback                    # Add this line
from ddtrace import tracer         # Add this line

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
from datetime import datetime, date, time
from threading import Lock

from .models import SessionState, SessionStats, ScanEvent
from . import db

session_configs = defaultdict(lambda: _load_default_from_file())

# In-memory session-scoped tracking for /done, /ping, /reset
sessions = defaultdict(lambda: {"count": 0, "last_ping": datetime.now(), "start_time": None})

main = Blueprint("main", __name__)

ADMIN_CLEAR_PASSWORD = "3.1415!"   # reuse same password

def _load_default_from_file() -> dict:
    return _load_golden_standard()

# --- Database-backed session state helpers ---
def get_session_state(session_id):
    record = SessionState.query.filter_by(session_id=session_id).first()
    # Always return a dict, never None
    return record.state if record and record.state is not None else {}

def set_session_state(session_id, state):
    print(f"🔧 DEBUG: Saving session '{session_id}' with state: {state}")
    try:
        record = SessionState.query.filter_by(session_id=session_id).first()
        if record:
            print(f"🔧 DEBUG: Updating existing session '{session_id}'")
            record.state = state
        else:
            print(f"🔧 DEBUG: Creating new session '{session_id}'")
            record = SessionState(session_id=session_id, state=state)
            db.session.add(record)
        db.session.commit()
        print(f"🔧 DEBUG: Session '{session_id}' saved successfully")
    except Exception as e:
        print(f"❌ ERROR: Failed to save session '{session_id}': {e}")
        db.session.rollback()
        raise

def get_next_session_sequence_id():
    """Get the next auto-incrementing session sequence ID"""
    try:
        # Get the highest existing sequence ID
        max_sequence = db.session.query(db.func.max(SessionStats.session_sequence_id)).scalar()
        return (max_sequence or 0) + 1
    except Exception as e:
        print(f"❌ Error getting next sequence ID: {e}")
        return 1  # Start from 1 if there's an error

# --- Routes ---

@main.route("/")
def home():
    return render_template("popup.html")

@main.route("/settings")
def settings():
    return render_template("settings.html")

@main.route("/statistics")
def statistics():
    import time
    timestamp = int(time.time())
    return render_template("statistics.html", cache_bust=timestamp)

@main.route("/statistics-v2")
def statistics_v2():
    import time
    timestamp = int(time.time())
    return render_template("statistics.html", cache_bust=timestamp)

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
    # If no session ID or "default", always load golden standard
    if not session_id or session_id == "default":
        content = _load_golden_standard()
    else:
        content = get_session_state(session_id)
        # If no session data, fallback to golden standard
        if not content:
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
        print(f"🔧 DEBUG: POST /api/session-state called for session '{session_id}'")
        try:
            data = request.get_json(force=True)
            print(f"🔧 DEBUG: Received data: {data}")
        except Exception as e:
            print(f"❌ ERROR: Invalid JSON in POST request: {e}")
            return jsonify({"error": f"Invalid JSON: {e}"}), 400
        set_session_state(session_id, data)
        return jsonify({"ok": True})

@main.route("/done")
def done():
    session_id = request.args.get("session", "default")
    current_time = datetime.now()
    
    # Update in-memory counter
    sessions[session_id]["count"] += 1
    sessions[session_id]["last_ping"] = current_time
    
    # Record scan event in database if we have a start time
    if sessions[session_id]["start_time"]:
        scan_time_relative = int((current_time - sessions[session_id]["start_time"]).total_seconds())
        try:
            scan_event = ScanEvent(
                session_id=session_id,
                scan_time_relative=scan_time_relative
            )
            db.session.add(scan_event)
            
            # Update finishing_green_dots count
            session_stats = SessionStats.query.filter_by(session_id=session_id).first()
            if session_stats:
                session_stats.finishing_green_dots = sessions[session_id]["count"]
                session_stats.updated_at = current_time
            
            db.session.commit()
            print(f"📊 Recorded scan event for session {session_id} at {scan_time_relative}s")
        except Exception as e:
            print(f"❌ Error recording scan event: {e}")
            db.session.rollback()
    
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
    current_time = datetime.now()
    
    # Reset in-memory counters
    sessions[session_id]["count"] = 0
    sessions[session_id]["last_ping"] = current_time
    sessions[session_id]["start_time"] = current_time  # Mark timer start
    
    # Initialize or reset session stats in database
    try:
        # Get session configuration to determine initial values
        session_state = get_session_state(session_id)
        countdown_duration = (session_state.get('minutes', 0) * 60) + session_state.get('seconds', 0)
        starting_red_dots = session_state.get('red_teams', 0)
        
        # Create or update session stats
        session_stats = SessionStats.query.filter_by(session_id=session_id).first()
        if session_stats:
            # Update existing record - reset for new session run
            session_stats.countdown_duration = countdown_duration
            session_stats.starting_red_dots = starting_red_dots
            session_stats.finishing_green_dots = 0
            session_stats.updated_at = current_time
            # Update session metadata for new run
            session_stats.session_date = current_time.date()
            session_stats.session_time_utc = current_time.time()
            session_stats.session_status = 'active'
            # Reset calculated fields (will be recalculated as scans come in)
            session_stats.median_completion_time = None
            session_stats.completion_quartiles = None
            session_stats.early_completion_rate = None
            session_stats.late_completion_rate = None
            session_stats.participation_rate = None
            session_stats.completion_spread = None
            session_stats.peak_completion_period = None
        else:
            # Create new record with enhanced metadata
            session_stats = SessionStats(
                session_id=session_id,
                countdown_duration=countdown_duration,
                starting_red_dots=starting_red_dots,
                finishing_green_dots=0,
                # Enhanced session metadata
                session_sequence_id=get_next_session_sequence_id(),
                session_date=current_time.date(),
                session_time_utc=current_time.time(),
                lab_name=session_id,  # Option A: lab_name = session_id
                session_status='active'
            )
            db.session.add(session_stats)
        
        # Clear any existing scan events for this session (fresh start)
        ScanEvent.query.filter_by(session_id=session_id).delete()
        
        db.session.commit()
        sequence_id = session_stats.session_sequence_id or "existing"
        print(f"📊 Initialized session stats for {session_id} (seq#{sequence_id}): {countdown_duration}s, {starting_red_dots} dots")
    except Exception as e:
        print(f"❌ Error initializing session stats: {e}")
        db.session.rollback()
    
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

@main.route("/force-error")
def force_error():
    """Route to force different types of errors for testing"""
    error_type = request.args.get('type', 'db')
    
    # Get the current span FIRST
    span = tracer.current_span()
    
    if error_type == 'db':
        try:
            db.session.execute('SELECT * FROM non_existent_table')
        except Exception as e:
            # Tag the error immediately
            if span:
                span.set_tag('error.type', type(e).__name__)
                span.set_tag('error.message', str(e))
                span.set_tag('error.stack', traceback.format_exc())
                span.error = True  # Try True instead of 1
            raise
    elif error_type == 'exception':
        # Tag error BEFORE raising
        if span:
            span.set_tag('error.type', 'ValueError')
            span.set_tag('error.message', 'Forced error for testing')
            span.error = True
        raise ValueError("Forced error for testing")
    
    return "This shouldn't be reached"

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

@main.route("/api/session-statistics", methods=["GET"])
def api_session_statistics():
    session_id = request.args.get("session", "default")
    
    try:
        # Get session stats
        session_stats = SessionStats.query.filter_by(session_id=session_id).first()
        if not session_stats:
            return jsonify({"error": "No statistics found for this session"}), 404
        
        # Get scan events
        scan_events = ScanEvent.query.filter_by(session_id=session_id).order_by(ScanEvent.scan_time_relative).all()
        
        # Format scan events for display
        scan_data = []
        for i, event in enumerate(scan_events, 1):
            minutes = event.scan_time_relative // 60
            seconds = event.scan_time_relative % 60
            scan_data.append({
                "dot_number": i,
                "time_relative": event.scan_time_relative,
                "time_formatted": f"{minutes}:{seconds:02d}"
            })
        
        # Calculate metrics
        completion_rate = (session_stats.finishing_green_dots / session_stats.starting_red_dots * 100) if session_stats.starting_red_dots > 0 else 0
        
        # Calculate average completion time (average of all scan times)
        avg_completion_time = 0
        if scan_events:
            total_time = sum(event.scan_time_relative for event in scan_events)
            avg_completion_time = total_time / len(scan_events)
        
        # Time to first and last scan
        time_to_first_scan = scan_events[0].scan_time_relative if scan_events else 0
        time_to_last_scan = scan_events[-1].scan_time_relative if scan_events else 0
        
        # Format enhanced metadata for display
        session_date_formatted = session_stats.session_date.isoformat() if session_stats.session_date else None
        session_time_formatted = session_stats.session_time_utc.strftime("%H:%M UTC") if session_stats.session_time_utc else None
        
        return jsonify({
            # Original fields
            "session_id": session_id,
            "countdown_duration": session_stats.countdown_duration,
            "starting_red_dots": session_stats.starting_red_dots,
            "finishing_green_dots": session_stats.finishing_green_dots,
            "completion_rate": round(completion_rate, 1),
            "avg_completion_time": round(avg_completion_time / 60, 2),  # in minutes
            "time_to_first_scan": round(time_to_first_scan / 60, 2),  # in minutes
            "time_to_last_scan": round(time_to_last_scan / 60, 2),  # in minutes
            "scan_events": scan_data,
            
            # Enhanced session metadata
            "session_sequence_id": session_stats.session_sequence_id,
            "session_date": session_date_formatted,
            "session_time": session_time_formatted,
            "lab_name": session_stats.lab_name,
            "session_status": session_stats.session_status,
            "session_duration_actual": round(session_stats.session_duration_actual / 60, 2) if session_stats.session_duration_actual else None,
            
            # Completion analytics (will be calculated in future steps)
            "median_completion_time": round(session_stats.median_completion_time / 60, 2) if session_stats.median_completion_time else None,
            "completion_quartiles": session_stats.completion_quartiles,
            "early_completion_rate": round(session_stats.early_completion_rate, 1) if session_stats.early_completion_rate else None,
            "late_completion_rate": round(session_stats.late_completion_rate, 1) if session_stats.late_completion_rate else None,
            "participation_rate": round(session_stats.participation_rate, 1) if session_stats.participation_rate else None,
            "completion_spread": round(session_stats.completion_spread / 60, 2) if session_stats.completion_spread else None,
            "peak_completion_period": session_stats.peak_completion_period
        })
    except Exception as e:
        print(f"❌ Error fetching session statistics: {e}")
        return jsonify({"error": "Failed to fetch statistics"}), 500