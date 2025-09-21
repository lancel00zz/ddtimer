# Visual State Synchronization Issues

## Issue: Timer Display vs Database State Mismatch

### Problem Description
When accessing a session with completed scans (e.g., `lab999`), there's a visual inconsistency:

- **Database/Statistics**: Shows 17 completed scans (100% completion rate)
- **Timer Display**: Shows 17 red dots on the left (appears as 0% completion)
- **Expected Behavior**: Should show 17 green dots on the right to match statistics

### Impact
- **User Confusion**: Visual state contradicts statistical data
- **UX Issue**: Misleading completion status
- **Data Integrity Perception**: Makes statistics appear unreliable

### Root Cause Analysis
The timer display state is managed in-memory and resets when switching sessions, but the database retains the completion data. The visual dot rendering doesn't sync with the database state on session load.

### Affected Files
- `app/templates/popup.html` - Timer display logic
- `app/routes.py` - Session state management
- Database: `ScanEvent` and `SessionStats` tables

### Solution Approach
1. **Extend session sync function** to include visual state
2. **Update dot rendering logic** to reflect database completion status
3. **Sync dot colors/positions** when session is loaded
4. **Ensure real-time updates** maintain consistency

### Related Work
- Session state synchronization implemented in `feature/statistics-v2`
- `sync_session_with_database()` function already handles count synchronization
- Need to extend this to handle visual dot state

### Test Cases
- [ ] Load session with partial completion (e.g., 5/10 scans)
- [ ] Load session with full completion (e.g., 17/17 scans)
- [ ] Switch between sessions and verify visual consistency
- [ ] Test with zero completion sessions
- [ ] Verify real-time updates work correctly

### Priority
- **Medium-High**: Affects user trust in data accuracy
- **User Experience**: Critical for completed sessions
- **Data Visualization**: Important for session reviews

### Implementation Notes
- Consider extending `sessions[session_id]` to track visual state
- May need to track individual dot IDs and their completion status
- Should integrate with existing session persistence logic
- Test thoroughly to avoid breaking active timer functionality

---
*Created: September 2025*  
*Related Branch: feature/statistics-v2*  
*Status: Documented, Ready for Implementation*
