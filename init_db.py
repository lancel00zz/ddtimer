from app import create_app, db
from sqlalchemy import text

def migrate_session_stats_table():
    """Add new columns to session_stats table if they don't exist"""
    try:
        # Check if new columns exist
        result = db.session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'session_stats' 
            AND column_name = 'session_sequence_id'
        """))
        
        if result.fetchone() is None:
            print("🔄 Adding enhanced statistics columns to session_stats table...")
            
            # Add all new columns
            db.session.execute(text("""
                ALTER TABLE session_stats 
                ADD COLUMN IF NOT EXISTS session_sequence_id INTEGER,
                ADD COLUMN IF NOT EXISTS session_date DATE,
                ADD COLUMN IF NOT EXISTS session_time_utc TIME,
                ADD COLUMN IF NOT EXISTS lab_name VARCHAR,
                ADD COLUMN IF NOT EXISTS session_duration_actual INTEGER,
                ADD COLUMN IF NOT EXISTS median_completion_time FLOAT,
                ADD COLUMN IF NOT EXISTS completion_quartiles JSONB,
                ADD COLUMN IF NOT EXISTS early_completion_rate FLOAT,
                ADD COLUMN IF NOT EXISTS late_completion_rate FLOAT,
                ADD COLUMN IF NOT EXISTS participation_rate FLOAT,
                ADD COLUMN IF NOT EXISTS completion_spread INTEGER,
                ADD COLUMN IF NOT EXISTS peak_completion_period VARCHAR,
                ADD COLUMN IF NOT EXISTS session_status VARCHAR(20) DEFAULT 'active'
            """))
            
            db.session.commit()
            print("✅ Enhanced statistics columns added successfully!")
        else:
            print("✅ Enhanced statistics columns already exist.")
            
    except Exception as e:
        print(f"⚠️  Migration error (this is normal for new databases): {e}")
        db.session.rollback()

app = create_app()
with app.app_context():
    # Create all tables (for new databases)
    db.create_all()
    print("📊 Database tables created/verified.")
    
    # Run migrations (for existing databases)
    migrate_session_stats_table()
    
    print("🎉 Database initialization complete!")