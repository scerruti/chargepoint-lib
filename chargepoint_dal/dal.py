import threading
import time
import json
from typing import Any, Dict, List, Optional

# Optionally import python-chargepoint if available
try:
    from python_chargepoint import ChargePoint
except ImportError:
    ChargePoint = None

class RateLimiter:
    """
    Simple token bucket rate limiter.
    Allows up to 'rate' requests per 'per' seconds.
    """
    def __init__(self, rate: int, per: float):
        self.rate = rate
        self.per = per
        self.allowance = rate
        self.last_check = time.monotonic()
        self.lock = threading.Lock()

    def acquire(self):
        with self.lock:
            current = time.monotonic()
            elapsed = current - self.last_check
            self.last_check = current
            self.allowance += elapsed * (self.rate / self.per)
            if self.allowance > self.rate:
                self.allowance = self.rate
            if self.allowance < 1.0:
                sleep_time = (1.0 - self.allowance) * (self.per / self.rate)
                time.sleep(sleep_time)
                self.allowance = 0
            else:
                self.allowance -= 1.0

class ChargePointDAL:
    """
    Caching, rate-limited data access layer for ChargePoint API.
    """
    def get_session_activity(self, session_id: str, include_samples: bool = True) -> Optional[Dict[str, Any]]:
        """
        Retrieve detailed activity for a specific session, with caching.
        Args:
            session_id: The session ID to fetch details for
            include_samples: Whether to include power samples (default: True)
        Returns:
            Session activity dict, or None if not found
        """
        import logging
        import os
        import json
        logging.basicConfig(level=logging.DEBUG)
        logger = logging.getLogger("ChargePointDAL")

        # Try to load from per-session cache file first
        session_cache_dir = "data/session_cache"
        found_file = None
        for root, dirs, files in os.walk(session_cache_dir):
            for file in files:
                if file == f"{session_id}.json":
                    found_file = os.path.join(root, file)
                    break
            if found_file:
                break
        if found_file:
            logger.debug(f"Loading session activity from cache file: {found_file}")
            try:
                with open(found_file, "r") as f:
                    data = json.load(f)
                return data
            except Exception as e:
                logger.error(f"Failed to load session cache file: {e}")
                # Fallback to legacy cache/API

        cache_key = f"session_activity_{session_id}_{'samples' if include_samples else 'nosamples'}"
        logger.debug(f"Checking cache for key: {cache_key}")
        with self.lock:
            if cache_key in self.cache:
                logger.debug(f"Cache hit for {cache_key}")
                return self.cache[cache_key]
            else:
                logger.debug(f"Cache miss for {cache_key}")

        payload = {"charging_status": {"mfhs": {}, "session_id": int(session_id)}}
        logger.debug(f"Sending API request for session_id={session_id}, include_samples={include_samples}")
        response = self.client.session.post(
            self.client.global_config.endpoints.mapcache + "v2",
            json=payload
        )
        self.ratelimiter.acquire()
        logger.debug(f"API response status: {response.status_code}")
        try:
            data = response.json()
            logger.debug(f"API response JSON: {data}")
        except Exception as e:
            logger.error(f"Failed to parse API response JSON: {e}")
            data = None
        with self.lock:
            self.cache[cache_key] = data
            self._save_cache()
        return data

    def __init__(self, username: str, password: str, cache_path: Optional[str] = None,
                 rate_limit: int = 6, rate_period: float = 60.0,
                 session_token_path: Optional[str] = None,
                 git_commit_enabled: bool = False):
        """
        Args:
            username: ChargePoint account username
            password: ChargePoint account password
            cache_path: Path to cache file (optional, defaults to data/cache/chargepoint_dal_cache.json)
            rate_limit: Max requests per rate_period (default: 6/min)
            rate_period: Time window for rate limiting in seconds
                session_token_path: Path to session token cache file (optional, defaults to data/cache/cp_session_token.txt)
        """

        if ChargePoint is None:
            raise ImportError("python-chargepoint is required for ChargePointDAL")

        if session_token_path is None:
            session_token_path = "data/cache/cp_session_token.txt"
        self.session_token_path = session_token_path

        session_token = self._load_session_token()
        try:
            if session_token:
                self.client = ChargePoint(username=username, password=password, session_token=session_token)
            else:
                self.client = ChargePoint(username=username, password=password)
        except Exception:
            # If session token is expired or invalid, fallback to login
            self.client = ChargePoint(username=username, password=password)
        # Always cache the latest session token after login
        self._save_session_token(self.client.session_token)

        self.cache_path = cache_path or "data/cache/chargepoint_dal_cache.json"
        self.cache: Dict[str, Any] = {}
        self.lock = threading.Lock()
        self.ratelimiter = RateLimiter(rate_limit, rate_period)
        self.git_commit_enabled = git_commit_enabled
        self._load_cache()

    def _load_session_token(self) -> Optional[str]:
        try:
            with open(self.session_token_path, "r") as f:
                token = f.read().strip()
                return token if token else None
        except Exception:
            return None

    def _save_session_token(self, token: Optional[str]):
        if not token:
            return
        try:
            with open(self.session_token_path, "w") as f:
                f.write(token)
        except Exception:
            pass

    def _load_cache(self):
        # Load legacy cache if present
        try:
            with open(self.cache_path, "r") as f:
                self.cache = json.load(f)
        except Exception:
            self.cache = {}

    def _save_cache(self):
        import os, json, subprocess
        # Save legacy cache for backward compatibility
        if self.cache_path:
            with open(self.cache_path, "w") as f:
                json.dump(self.cache, f)
            if getattr(self, "git_commit_enabled", False):
                cache_abspath = os.path.abspath(self.cache_path)
                try:
                    subprocess.run(["git", "add", cache_abspath], check=True)
                    status = subprocess.run(["git", "status", "--porcelain", cache_abspath], capture_output=True, text=True)
                    if status.stdout.strip():
                        subprocess.run(["git", "commit", "-m", "Update ChargePoint DAL cache"], check=True)
                except subprocess.CalledProcessError as e:
                    print(f"Warning: git command failed: {e}")
                except Exception as e:
                    print(f"Warning: git commit logic error: {e}")
        # Save per-month session summaries
        print("[DAL DEBUG] Cache keys:")
        for key in self.cache.keys():
            print(f"  [DAL DEBUG] {key}")
        for key, value in self.cache.items():
            if key.startswith("sessions_") and isinstance(value, list):
                print(f"[DAL DEBUG] Considering key for per-month summary: {key}")
                # Try to extract year/month from key (look for p_{year}_{month})
                import re
                match = re.search(r"p_(\d{4})_(\d{2})", key)
                if match:
                    y, m = match.group(1), match.group(2)
                    print(f"[DAL DEBUG] Writing per-month summary for {y}-{m}")
                    month_path = f"data/cache/sessions/{y}/{m}.json"
                    os.makedirs(os.path.dirname(month_path), exist_ok=True)
                    with open(month_path, "w") as f:
                        json.dump(value, f)
                    if getattr(self, "git_commit_enabled", False):
                        month_abspath = os.path.abspath(month_path)
                        try:
                            subprocess.run(["git", "add", month_abspath], check=True)
                            status = subprocess.run(["git", "status", "--porcelain", month_abspath], capture_output=True, text=True)
                            if status.stdout.strip():
                                subprocess.run(["git", "commit", "-m", f"Update session summaries for {y}-{m}"], check=True)
                        except subprocess.CalledProcessError as e:
                            print(f"Warning: git command failed: {e}")
                        except Exception as e:
                            print(f"Warning: git commit logic error: {e}")
        # Save per-session activity details
        for key, value in self.cache.items():
            if key.startswith("session_activity_") and isinstance(value, dict):
                # Try to extract session_id from key
                parts = key.split("_")
                if len(parts) >= 3:
                    session_id = parts[2]
                    # Optionally extract year/month from value
                    start_time = None
                    if "charging_status" in value and "start_time" in value["charging_status"]:
                        import datetime
                        ts = value["charging_status"]["start_time"] // 1000
                        dt = datetime.datetime.utcfromtimestamp(ts)
                        y, m = dt.year, f"{dt.month:02d}"
                        session_path = f"data/session_cache/{y}/{m}/{session_id}.json"
                        os.makedirs(os.path.dirname(session_path), exist_ok=True)
                        with open(session_path, "w") as f:
                            json.dump(value, f)
                        if getattr(self, "git_commit_enabled", False):
                            session_abspath = os.path.abspath(session_path)
                            try:
                                subprocess.run(["git", "add", session_abspath], check=True)
                                status = subprocess.run(["git", "status", "--porcelain", session_abspath], capture_output=True, text=True)
                                if status.stdout.strip():
                                    subprocess.run(["git", "commit", "-m", f"Update session activity {session_id}"], check=True)
                            except subprocess.CalledProcessError as e:
                                print(f"Warning: git command failed: {e}")
                            except Exception as e:
                                print(f"Warning: git commit logic error: {e}")

    def get_sessions(self, max_batches: int = 10, batch_size: int = 10, year: int = None, month: int = None) -> List[Dict[str, Any]]:
        """
        Fetches charging sessions with 'Smart Stop' logic to prevent API bans.
        Checks batch timestamps to stop as soon as we pass the target month.
        """
        import os, json, datetime
        
        if year is None or month is None:
            raise ValueError("Year and month must be specified")
            
        cache_key = f"sessions_{year}_{month:02d}"
        cache_path = f"data/cache/sessions/{year}/{month:02d}.json"
        now = datetime.datetime.utcnow()
        
        # Calculate strict boundaries for the target month
        start_of_target = datetime.datetime(year, month, 1)
        if month == 12:
            end_of_target = datetime.datetime(year + 1, 1, 1)
        else:
            end_of_target = datetime.datetime(year, month + 1, 1)

        # 1. Try to load cache file first (Safe: No API calls)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r") as f:
                    cache_data = json.load(f)
                date_retrieved = cache_data.get("date_retrieved")
                if date_retrieved:
                    retrieved_dt = datetime.datetime.fromisoformat(date_retrieved)
                    # If we cached this AFTER the month ended, the data is final. Use it.
                    if retrieved_dt >= end_of_target:
                        return cache_data.get("sessions", [])
            except Exception as e:
                print(f"[DAL ERROR] Failed to load cache: {e}")

        # 2. Fetch from API (Carefully)
        sessions = []
        page_offset = f"p_{year}_{month:02d}" # Starting hint, but we might need to scroll
        
        # NOTE: If we are looking for a past month, we might need to start blank 
        # to let the API give us the newest and scroll back. 
        # However, keeping your existing offset logic for now as it seems to be a ChargePoint optimization.
        payload = {
            "charging_activity_monthly": {
                "page_size": batch_size, 
                "show_address_for_home_sessions": True, 
                "page_offset": page_offset
            }
        }
        
        last_offset = None

        for i in range(max_batches):
            print(f"[DAL DEBUG] Fetching batch {i+1}/{max_batches}...")
            
            # -- API CALL --
            response = self.client.session.post(
                self.client.global_config.endpoints.mapcache + "v2",
                json=payload
            )
            self.ratelimiter.acquire() # Strict adherence to your rate limit
            # --------------

            try:
                data = response.json()
            except json.JSONDecodeError:
                print("[DAL ERROR] API returned non-JSON response")
                break

            # Extract sessions from the messy response structure
            batch_sessions = []
            next_offset = None
            
            # Support both API response formats
            if "charging_activity" in data and "sessions" in data["charging_activity"]:
                batch_sessions = data["charging_activity"]["sessions"]
                next_offset = data["charging_activity"].get("page_offset")
            elif "charging_activity_monthly" in data:
                month_info = data["charging_activity_monthly"].get("month_info")
                if month_info and isinstance(month_info, list) and len(month_info) > 0:
                    batch_sessions = month_info[0].get("sessions", [])
                next_offset = data["charging_activity_monthly"].get("page_offset")

            if not batch_sessions:
                print(f"[DAL DEBUG] Batch {i+1} empty. Stopping.")
                break

            # 3. Analyze Batch Timestamps for "Smart Stop"
            batch_dates = []
            for s in batch_sessions:
                st = s.get("start_time") or s.get("startTime")
                if st:
                    if isinstance(st, int) and st > 1000000000000:
                        batch_dates.append(datetime.datetime.utcfromtimestamp(st / 1000))
                    else:
                        try:
                            batch_dates.append(datetime.datetime.fromisoformat(st))
                        except:
                            pass
            
            if not batch_dates:
                print("[DAL WARNING] Could not parse dates in batch. Skipping safety checks.")
                # Fallback: Just filter and continue
            else:
                earliest_in_batch = min(batch_dates)
                latest_in_batch = max(batch_dates)

                # CASE A: We are entirely in the future (Newer than target month)
                if earliest_in_batch >= end_of_target:
                    print(f"[DAL INFO] Batch is too new ({earliest_in_batch} > {end_of_target}). Scrolling back...")
                    # Do NOT break. We need to keep fetching to reach our month.
                
                # CASE B: We have gone past the target (Older than target month)
                elif latest_in_batch < start_of_target:
                    print(f"[DAL INFO] Batch is too old ({latest_in_batch} < {start_of_target}). Data complete. STOP.")
                    break # <--- SAFETY STOP
            
            # 4. Filter and Store Matches
            for s in batch_sessions:
                # (Re-parsing just for filtering - minimal overhead)
                st = s.get("start_time") or s.get("startTime")
                if st:
                    if isinstance(st, int): dt = datetime.datetime.utcfromtimestamp(st / 1000)
                    else: 
                        try: dt = datetime.datetime.fromisoformat(st)
                        except: continue
                    
                    if dt.year == year and dt.month == month:
                        sessions.append(s)

            # 5. Pagination Logic
            if next_offset == "last_page" or not next_offset or next_offset == last_offset:
                break
            
            last_offset = next_offset
            payload["charging_activity_monthly"]["page_offset"] = next_offset

        # Save to cache
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        cache_data = {"sessions": sessions, "date_retrieved": now.isoformat()}
        with open(cache_path, "w") as f:
            json.dump(cache_data, f)
            
        # Update memory cache
        with self.lock:
            self.cache[cache_key] = sessions
            
        return sessions

    # Additional methods for fetching session details, status, etc. can be added here
