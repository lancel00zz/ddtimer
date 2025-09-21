# Testing Enhanced Statistics - Manual Approach

Since the test data script requires the full Flask environment, here's a **manual testing approach** that's actually more realistic:

## 🧪 **Manual Testing Steps**

### **Test Session 1: Quick Lab (test_quick)**
1. **Open app**: `http://localhost:5000/?session=test_quick`
2. **Configure session**:
   - Timer: 30 minutes
   - Teams: 12
3. **Start timer** and **simulate quick completion**:
   - Scan QR codes at: 5min, 8min, 10min, 12min, 15min, 18min, 20min, 22min
   - This simulates most teams finishing in first 50% of time

### **Test Session 2: Hard Lab (test_hard)**
1. **Open app**: `http://localhost:5000/?session=test_hard`
2. **Configure session**:
   - Timer: 90 minutes (1h 30m)
   - Teams: 15
3. **Start timer** and **simulate spread completion**:
   - Scan QR codes at: 15min, 25min, 35min, 45min, 55min, 65min, 75min, 80min, 85min
   - This simulates teams spread across all quartiles

### **Test Session 3: Long Lab (test_long)**
1. **Open app**: `http://localhost:5000/?session=test_long`
2. **Configure session**:
   - Timer: 120 minutes (2h)
   - Teams: 10
3. **Start timer** and **simulate late completion**:
   - Scan QR codes at: 70min, 80min, 90min, 95min, 100min, 105min, 110min
   - This simulates most teams finishing in last 50% of time

## 📊 **What to Verify**

After each test session, click the **statistics button** (chart icon) and verify:

### **Basic Metadata** ✅
- Session date shows today's date
- Session time shows UTC time when started
- Lab name matches session ID (test_quick, test_hard, test_long)
- Session sequence ID increments (1, 2, 3...)

### **Completion Analytics** (Will be implemented in Step 4)
- Median completion time
- Completion quartiles (Q1, Q2, Q3)
- Early completion rate (% in first 50%)
- Late completion rate (% in last 25%)
- Participation rate

## 🎯 **Expected Results**

### **test_quick** (30min lab, most finish early):
- Early completion rate: ~80%
- Late completion rate: ~10%
- Median: Around 15 minutes

### **test_hard** (90min lab, spread out):
- Early completion rate: ~40%
- Late completion rate: ~25%
- Median: Around 45 minutes

### **test_long** (120min lab, most finish late):
- Early completion rate: ~20%
- Late completion rate: ~70%
- Median: Around 90 minutes

## 🚀 **Quick Test Script Alternative**

If you want to test the database fields directly, you can:

1. **Start the app** (Docker or local)
2. **Create a session** and run it manually
3. **Check the database** directly:

```sql
-- Connect to your PostgreSQL database
SELECT 
    session_sequence_id,
    session_id,
    lab_name,
    session_date,
    session_time_utc,
    starting_red_dots,
    finishing_green_dots,
    session_status
FROM session_stats 
ORDER BY session_sequence_id DESC;
```

This will show you that the new fields are being populated correctly!

## ✅ **Ready for Step 4**

Once you've verified that:
- ✅ Sessions get unique sequence IDs
- ✅ Session metadata is populated (date, time, lab_name)
- ✅ Session status is set correctly

We can proceed to **Step 4: Statistics Calculation Functions** to compute the completion analytics!
