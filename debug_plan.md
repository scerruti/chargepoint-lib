# Debug Plan: DAL Session Activity Retrieval

## Steps

1. **Confirm DAL logic for reading session cache files**
   - Ensure DAL loads and parses data/sessions/YYYY/MM/DD/{session_id}.json.
2. **Add logging to DAL’s get_session_activity**
   - Trace file access and parsing steps.
3. **Test DAL retrieval for session 4751613101**
   - Should now return the full activity from the cache file.
4. **If still empty, check for schema mismatches or parsing errors**
   - Compare expected vs. actual JSON structure.
5. **Validate fallback logic**
   - Ensure DAL tries API, cache, and sessions folder in correct order.
   - Check error handling and fallback behavior.

---
Paused as requested. Resume when ready.
