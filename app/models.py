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