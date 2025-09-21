from . import db
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

class SessionState(db.Model):
    __tablename__ = 'session_states'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String, unique=True, nullable=False)
    state = db.Column(JSONB, nullable=False)

class SessionStats(db.Model):
    __tablename__ = 'session_stats'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String, unique=True, nullable=False)
    countdown_duration = db.Column(db.Integer, nullable=False)  # in seconds
    starting_red_dots = db.Column(db.Integer, nullable=False)
    finishing_green_dots = db.Column(db.Integer, default=0)
    
    # Enhanced session metadata
    session_sequence_id = db.Column(db.Integer, nullable=True)  # Auto-incrementing unique ID
    session_date = db.Column(db.Date, nullable=True)  # Date when session was run
    session_time_utc = db.Column(db.Time, nullable=True)  # UTC time when session started
    lab_name = db.Column(db.String, nullable=True)  # Extracted/derived lab name
    session_duration_actual = db.Column(db.Integer, nullable=True)  # Actual session duration in seconds
    
    # Completion time statistics
    median_completion_time = db.Column(db.Float, nullable=True)  # Median time in seconds
    completion_quartiles = db.Column(JSONB, nullable=True)  # Q1, Q2, Q3 times
    
    # Completion rate analytics
    early_completion_rate = db.Column(db.Float, nullable=True)  # % finishing in first 50% of time
    late_completion_rate = db.Column(db.Float, nullable=True)  # % finishing in last 25% of time
    participation_rate = db.Column(db.Float, nullable=True)  # % of teams that scanned at least once
    
    # Additional metrics
    completion_spread = db.Column(db.Integer, nullable=True)  # Time between first and last completion
    peak_completion_period = db.Column(db.String, nullable=True)  # Which quartile had most completions
    session_status = db.Column(db.String(20), default='active')  # active, completed, abandoned
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ScanEvent(db.Model):
    __tablename__ = 'scan_events'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String, nullable=False)
    scan_time_relative = db.Column(db.Integer, nullable=False)  # seconds from countdown start
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Index for faster queries by session
    __table_args__ = (db.Index('idx_scan_events_session_id', 'session_id'),)