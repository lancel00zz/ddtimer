#!/usr/bin/env python3
"""
Test data generator for enhanced statistics system.
Creates realistic test sessions with different completion patterns.

Usage:
    python create_test_data.py

This will create test sessions accessible via:
    /?session=test_quick    - Most teams finish early
    /?session=test_hard     - Spread across all quartiles  
    /?session=test_long     - Most teams finish late
    /?session=test_mixed    - Even distribution
"""

import sys
import os
from datetime import datetime, timedelta
import random

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app import create_app, db
from app.models import SessionStats, ScanEvent

def create_test_session(session_id, lab_name, countdown_minutes, teams, completion_pattern):
    """Create a test session with realistic data"""
    
    # Calculate session timing
    countdown_duration = countdown_minutes * 60  # Convert to seconds
    session_start = datetime.utcnow() - timedelta(hours=2)  # 2 hours ago
    
    print(f"Creating test session: {session_id}")
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
        session_status='completed',  # Mark as completed for testing
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
    
    print(f"  Created {len(scan_times)} scan events")
    return session_stats

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

def get_next_sequence_id():
    """Get the next sequence ID"""
    try:
        max_sequence = db.session.query(db.func.max(SessionStats.session_sequence_id)).scalar()
        return (max_sequence or 0) + 1
    except:
        return 1

def main():
    """Create all test sessions"""
    
    app = create_app()
    
    with app.app_context():
        print("🧪 Creating test data for enhanced statistics system...")
        print("=" * 60)
        
        # Clear existing test data
        print("Cleaning up existing test sessions...")
        SessionStats.query.filter(SessionStats.session_id.like('test_%')).delete()
        ScanEvent.query.filter(ScanEvent.session_id.like('test_%')).delete()
        
        # Create test sessions with different patterns
        test_sessions = [
            {
                'session_id': 'test_quick',
                'lab_name': 'lab01_intro',
                'countdown_minutes': 30,
                'teams': 12,
                'pattern': 'quick'
            },
            {
                'session_id': 'test_hard', 
                'lab_name': 'lab05_advanced',
                'countdown_minutes': 90,
                'teams': 15,
                'pattern': 'hard'
            },
            {
                'session_id': 'test_long',
                'lab_name': 'lab08_project',
                'countdown_minutes': 120,
                'teams': 10,
                'pattern': 'long'
            },
            {
                'session_id': 'test_mixed',
                'lab_name': 'lab03_workshop',
                'countdown_minutes': 60,
                'teams': 18,
                'pattern': 'mixed'
            }
        ]
        
        created_sessions = []
        
        for session_config in test_sessions:
            try:
                session_stats = create_test_session(**session_config)
                created_sessions.append(session_stats)
                print("  ✅ Success!")
                
            except Exception as e:
                print(f"  ❌ Error: {e}")
        
        # Commit all changes
        try:
            db.session.commit()
            print("\n" + "=" * 60)
            print("🎉 Test data created successfully!")
            print("\nYou can now test the enhanced statistics by visiting:")
            
            for session in created_sessions:
                print(f"  📊 /?session={session.session_id}")
                print(f"     Lab: {session.lab_name}")
                print(f"     Teams: {session.starting_red_dots} → {session.finishing_green_dots} completed")
                print(f"     Sequence ID: #{session.session_sequence_id}")
                print()
            
            print("Click the statistics button (chart icon) to see the enhanced metrics!")
            
        except Exception as e:
            print(f"\n❌ Error committing changes: {e}")
            db.session.rollback()

if __name__ == "__main__":
    main()
