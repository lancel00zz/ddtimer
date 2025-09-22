from app import create_app, db
from app.models import SessionState, SessionStats, ScanEvent
from sqlalchemy import text
from datetime import datetime, timedelta
import random

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

def get_next_sequence_id():
    """Get the next sequence ID"""
    try:
        max_sequence = db.session.query(db.func.max(SessionStats.session_sequence_id)).scalar()
        return (max_sequence or 0) + 1
    except:
        return 1

def generate_scan_times(countdown_duration, total_teams, pattern):
    """Generate realistic scan times based on completion pattern"""
    
    # Determine how many teams will actually scan (participation rate)
    if pattern == "quick":
        participation = 0.95  # High participation for easy labs
        num_scanning = int(total_teams * participation)
    elif pattern == "hard":
        participation = 0.75  # Lower participation for hard labs
        num_scanning = int(total_teams * participation)
    elif pattern == "long":
        participation = 0.85  # Medium participation
        num_scanning = int(total_teams * participation)
    else:  # mixed
        participation = 0.90  # Good participation
        num_scanning = int(total_teams * participation)
    
    scan_times = []
    
    for i in range(num_scanning):
        if pattern == "quick":
            # Most finish in first 50% of time (Q1-Q2)
            if random.random() < 0.8:  # 80% finish early
                scan_time = random.randint(int(countdown_duration * 0.1), int(countdown_duration * 0.5))
            else:  # 20% finish later
                scan_time = random.randint(int(countdown_duration * 0.5), int(countdown_duration * 0.9))
                
        elif pattern == "hard":
            # Spread across all quartiles with slight bias toward later
            quartile = random.choices([1, 2, 3, 4], weights=[15, 25, 35, 25])[0]
            q_start = (quartile - 1) * 0.25
            q_end = quartile * 0.25
            scan_time = random.randint(int(countdown_duration * q_start), int(countdown_duration * q_end))
            
        elif pattern == "long":
            # Most finish in last 50% of time (Q3-Q4)
            if random.random() < 0.75:  # 75% finish late
                scan_time = random.randint(int(countdown_duration * 0.5), int(countdown_duration * 0.95))
            else:  # 25% finish early
                scan_time = random.randint(int(countdown_duration * 0.1), int(countdown_duration * 0.5))
                
        else:  # mixed - even distribution
            scan_time = random.randint(int(countdown_duration * 0.1), int(countdown_duration * 0.9))
        
        scan_times.append(scan_time)
    
    # Sort scan times to be realistic (teams finish in somewhat chronological order)
    scan_times.sort()
    
    # Add some randomness to make it more realistic
    for i in range(len(scan_times)):
        if i > 0:  # Don't modify the first one
            # Small chance to swap with previous (teams finishing close together)
            if random.random() < 0.2:
                scan_times[i], scan_times[i-1] = scan_times[i-1], scan_times[i]
    
    return scan_times

def create_demo_session(session_id, lab_name, countdown_minutes, teams, completion_pattern):
    """Create a demo session with realistic data"""
    
    # Calculate session timing
    countdown_duration = countdown_minutes * 60  # Convert to seconds
    session_start = datetime.utcnow() - timedelta(hours=2)  # 2 hours ago
    
    print(f"Creating demo session: {session_id}")
    print(f"  Lab: {lab_name}")
    print(f"  Duration: {countdown_minutes} minutes")
    print(f"  Teams: {teams}")
    print(f"  Pattern: {completion_pattern}")
    
    # Create SessionStats record
    session_stats = SessionStats(
        session_id=session_id,
        countdown_duration=countdown_duration,
        starting_red_dots=teams,
        finishing_green_dots=0,  # Will be updated as we add scan events
        
        # Enhanced session metadata
        session_sequence_id=get_next_sequence_id(),
        session_date=session_start.date(),
        session_time_utc=session_start.time(),
        lab_name=lab_name,
        session_status='completed',  # Mark as completed for demo
        session_duration_actual=countdown_duration + random.randint(-300, 600)  # Slight variation
    )
    
    db.session.add(session_stats)
    db.session.flush()  # Get the ID
    
    # Generate scan events based on completion pattern
    scan_times = generate_scan_times(countdown_duration, teams, completion_pattern)
    
    for i, scan_time in enumerate(scan_times, 1):
        scan_event = ScanEvent(
            session_id=session_id,
            scan_time_relative=scan_time,
            created_at=session_start + timedelta(seconds=scan_time)
        )
        db.session.add(scan_event)
    
    # Update finishing_green_dots
    session_stats.finishing_green_dots = len(scan_times)
    
    # Create SessionState record for session validation
    session_state_data = {
        'minutes': countdown_minutes,
        'seconds': 0,
        'red_teams': teams,
        'green_teams': len(scan_times),  # Completed teams
        'dot_size': 'M',
        'dot_style': 'datadog_bits',
        'background_color': '#d0f0ff',
        'font_color': '#000000',
        'font_family': 'Oswald',
        'background_image': 'cannes_new.png',
        'custom_font_color_set': True,
        'contrast_mode': 'auto',
        'type': 'settings'
    }
    
    session_state = SessionState(
        session_id=session_id,
        state=session_state_data
    )
    db.session.add(session_state)
    
    print(f"  Created {len(scan_times)} scan events")
    print(f"  Created session state for UI validation")
    return session_stats

def create_demo_data():
    """Create demo sessions if they don't exist"""
    try:
        # Check if demo sessions already exist
        existing_demo_stats = SessionStats.query.filter(SessionStats.session_id.like('test%')).first()
        existing_demo_state = SessionState.query.filter(SessionState.session_id.like('test%')).first()
        
        if existing_demo_stats and existing_demo_state:
            print("✅ Demo sessions already exist, skipping creation.")
            return
        
        # Clean up any incomplete demo data
        if existing_demo_stats or existing_demo_state:
            print("🧹 Cleaning up incomplete demo data...")
            SessionStats.query.filter(SessionStats.session_id.like('test%')).delete()
            SessionState.query.filter(SessionState.session_id.like('test%')).delete()
            ScanEvent.query.filter(ScanEvent.session_id.like('test%')).delete()
            db.session.commit()
        
        print("🧪 Creating demo sessions for statistics showcase...")
        print("=" * 50)
        
        # Demo sessions with your preferred naming
        demo_sessions = [
            {
                'session_id': 'test001',
                'lab_name': 'Easy Lab Demo',
                'countdown_minutes': 30,
                'teams': 12,
                'completion_pattern': 'quick'
            },
            {
                'session_id': 'test002', 
                'lab_name': 'Challenging Lab Demo',
                'countdown_minutes': 90,
                'teams': 15,
                'completion_pattern': 'hard'
            },
            {
                'session_id': 'test003',
                'lab_name': 'Complex Project Demo',
                'countdown_minutes': 120,
                'teams': 10,
                'completion_pattern': 'long'
            },
            {
                'session_id': 'test004',
                'lab_name': 'Workshop Demo',
                'countdown_minutes': 60,
                'teams': 18,
                'completion_pattern': 'mixed'
            }
        ]
        
        created_sessions = []
        
        for session_config in demo_sessions:
            try:
                session_stats = create_demo_session(**session_config)
                # Commit each session individually to ensure data persistence
                db.session.commit()
                created_sessions.append(session_stats)
                print("  ✅ Success!")
                
            except Exception as e:
                print(f"  ❌ Error: {e}")
                db.session.rollback()
        print("\n" + "=" * 50)
        print("🎉 Demo sessions created successfully!")
        print("\nDemo sessions available:")
        
        for session in created_sessions:
            print(f"  📊 /?session={session.session_id}")
            print(f"     {session.lab_name}")
            print(f"     Teams: {session.starting_red_dots} → {session.finishing_green_dots} completed")
            print()
        
        print("Access any demo session and click the statistics button (chart icon)!")
        
    except Exception as e:
        print(f"❌ Error creating demo data: {e}")
        db.session.rollback()

app = create_app()
with app.app_context():
    # Create all tables (for new databases)
    db.create_all()
    print("📊 Database tables created/verified.")
    
    # Run migrations (for existing databases)
    migrate_session_stats_table()
    
    # Create demo data (auto-generate on first startup)
    create_demo_data()
    
    print("🎉 Database initialization complete!")