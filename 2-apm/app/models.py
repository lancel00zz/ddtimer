from . import db
from sqlalchemy.dialects.postgresql import JSONB

class SessionState(db.Model):
    __tablename__ = 'session_states'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String, unique=True, nullable=False)
    state = db.Column(JSONB, nullable=False)