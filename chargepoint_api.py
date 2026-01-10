#!/usr/bin/env python3
"""
Direct ChargePoint API client using undocumented /map-prod/v2 endpoint.

This bypasses the python-chargepoint library limitations and provides access to
the actual ChargePoint mobile/web API used by the driver app.

Endpoint: POST https://mc.chargepoint.com/map-prod/v2
"""

import os
import json
import requests
import re
from datetime import datetime
from typing import Optional, Dict, List, Any
from dotenv import load_dotenv

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

# Load environment variables
load_dotenv()


class ChargePointDirectAPI:
    """Direct HTTP client for ChargePoint API endpoints."""
    
    # Known endpoints
    MAP_PROD_URL = "https://mc.chargepoint.com/map-prod/v2"
    DRIVER_API_URL = "https://driver.chargepoint.com/api"
    CHARGING_ACTIVITY_URL = "https://driver.chargepoint.com/charging-activity"
    LOGIN_URL = "https://account.chargepoint.com/account/v1/driver/auth/login"
    
    def __init__(self, username: str, password: str):
        """Initialize with credentials and authenticate."""
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.auth_token = None
        self.authenticate()
    
    def authenticate(self) -> None:
        """Authenticate with ChargePoint and obtain session token."""
        print(f"🔐 Authenticating with ChargePoint as {self.username}...")
        
        payload = {
            "username": self.username,
            "password": self.password,
            "grant_type": "password"
        }
        
        try:
            response = self.session.post(
                self.LOGIN_URL,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            self.auth_token = data.get("auth_token") or data.get("access_token")
            
            if self.auth_token:
                print("✓ Authentication successful")
                # Set auth header for future requests
                self.session.headers.update({
                    "Authorization": f"Bearer {self.auth_token}"
                })
            else:
                raise Exception("No auth token in response")
        except Exception as e:
            raise Exception(f"Authentication failed: {e}")
    
    def _make_request(self, url: str, payload: Dict[str, Any], headers: Dict[str, str] = None) -> Dict[str, Any]:
        """Make a request to a ChargePoint API endpoint."""
        default_headers = {
            "accept": "application/json",
            "accept-language": "en-US",
            "content-type": "application/json",
            "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36"
        }
        
        if headers:
            default_headers.update(headers)
        
        try:
            response = self.session.post(
                url,
                json=payload,
                headers=default_headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"API request to {url} failed: {e}")
    
    def get_user_sessions(self) -> Optional[Dict[str, Any]]:
        """
        Get user's charging sessions and status via /map-prod/v2 endpoint.
        
        Returns:
            Dict with user status, charging sessions, and session history
        """
        payload = {
            "user_status": {
                "mfhs": {}
            }
        }
        
        headers = {
            "accept": "*/*",
            "origin": "https://driver.chargepoint.com",
            "referer": "https://driver.chargepoint.com/",
            "x-requested-with": "XMLHttpRequest"
        }
        
        try:
            result = self._make_request(self.MAP_PROD_URL, payload, headers)
            return result
        except Exception as e:
            print(f"Error fetching user sessions: {e}")
            return None
    
    def get_session_details(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific session.
        
        Args:
            session_id: The session ID to fetch details for
        
        Returns:
            Session details dict
        """
        payload = {
            "session_id": session_id,
            "include_samples": True
        }
        
        try:
            result = self._make_request(self.MAP_PROD_URL, payload)
            return result
        except Exception as e:
            print(f"Error fetching session {session_id}: {e}")
            return None
    
    def fetch_charging_activity_page(self) -> Optional[str]:
        """
        Fetch the charging-activity HTML page to extract session data.
        
        The page may contain embedded JSON data in script tags or make
        client-side API calls to fetch sessions.
        
        Returns:
            HTML content of the charging-activity page
        """
        try:
            response = self.session.get(
                self.CHARGING_ACTIVITY_URL,
                timeout=30
            )
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error fetching charging activity page: {e}")
            return None
    
    def extract_sessions_from_page(self, html: str) -> Optional[List[Dict[str, Any]]]:
        """
        Extract session data from charging-activity HTML page.
        
        Looks for:
        1. Embedded JSON in script tags
        2. Session IDs in HTML elements
        3. API endpoints referenced in JavaScript
        
        Args:
            html: HTML content from charging-activity page
        
        Returns:
            List of sessions or session IDs found
        """
        if not BS4_AVAILABLE:
            print("BeautifulSoup4 not available, trying regex parsing")
            # Simple regex approach
            session_ids = re.findall(r'session["\']?\s*[:=]\s*["\']?(\d+)', html, re.IGNORECASE)
            return list(set(session_ids)) if session_ids else None
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Look for embedded JSON in script tags
            for script in soup.find_all('script'):
                if script.string:
                    try:
                        # Try to parse as JSON
                        data = json.loads(script.string)
                        if isinstance(data, list):
                            return data
                        elif isinstance(data, dict) and "sessions" in data:
                            return data["sessions"]
                    except json.JSONDecodeError:
                        # Check for session IDs in the script content
                        ids = re.findall(r'session["\']?\s*[:=]\s*["\']?(\d+)', script.string)
                        if ids:
                            return list(set(ids))
            
            return None
        except Exception as e:
            print(f"Error parsing charging activity page: {e}")
            return None
    
    def get_session_history(self, page_size: int = 50, 
                           show_address: bool = True) -> Optional[Dict[str, Any]]:
        """
        Get a single page of charging activity history via /map-prod/v2 endpoint.
        Use get_session_history_paginated to retrieve all pages.
        """
        payload = {
            "charging_activity_monthly": {
                "page_size": page_size,
                "show_address_for_home_sessions": show_address
            }
        }
        
        headers = {
            "accept": "*/*",
            "origin": "https://driver.chargepoint.com",
            "referer": "https://driver.chargepoint.com/",
            "x-requested-with": "XMLHttpRequest"
        }
        
        try:
            result = self._make_request(self.MAP_PROD_URL, payload, headers)
            return result
        except Exception as e:
            print(f"Error fetching charging activity history: {e}")
            return None

    def get_session_history_paginated(self, page_size: int = 200, max_pages: int = 20,
                                      show_address: bool = True) -> List[Dict[str, Any]]:
        """
        Fetch all charging activity pages until depletion or max_pages.
        Returns a flat list of sessions.
        """
        headers = {
            "accept": "*/*",
            "origin": "https://driver.chargepoint.com",
            "referer": "https://driver.chargepoint.com/",
            "x-requested-with": "XMLHttpRequest"
        }

        all_sessions: List[Dict[str, Any]] = []
        seen_ids = set()

        for page in range(1, max_pages + 1):
            payload = {
                "charging_activity_monthly": {
                    "page_size": page_size,
                    "show_address_for_home_sessions": show_address,
                    "page_number": page
                }
            }

            try:
                result = self._make_request(self.MAP_PROD_URL, payload, headers)
            except Exception as e:
                print(f"Error fetching page {page}: {e}")
                break

            page_sessions = self.extract_sessions_from_activity(result)
            if not page_sessions:
                break

            new_count = 0
            for s in page_sessions:
                sid = s.get("session_id") or s.get("sessionId")
                if sid and sid not in seen_ids:
                    seen_ids.add(sid)
                    all_sessions.append(s)
                    new_count += 1

            if new_count == 0:
                # No new sessions found; stop to avoid infinite loop
                break

            # Heuristic: if fewer than page_size returned, likely last page
            if len(page_sessions) < page_size:
                break

        return all_sessions
    
    def extract_sessions_from_activity(self, activity_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract individual sessions from charging activity response.
        
        Args:
            activity_data: Response from get_session_history()
        
        Returns:
            Flat list of all sessions from the activity data
        """
        sessions = []
        
        if not isinstance(activity_data, dict):
            return sessions
        
        # The response structure likely contains monthly data
        # Try common keys for session data
        for key in ["charging_activity_monthly", "sessions", "activities", "data"]:
            if key in activity_data:
                data = activity_data[key]
                
                # If it's a list, add all items
                if isinstance(data, list):
                    sessions.extend(data)
                # If it's a dict with nested structure, look for sessions
                elif isinstance(data, dict):
                    if "sessions" in data:
                        sessions.extend(data["sessions"])
                    elif "activities" in data:
                        sessions.extend(data["activities"])
                    else:
                        # Try to find any list values that might be sessions
                        for v in data.values():
                            if isinstance(v, list) and v:
                                sessions.extend(v)
        
        return sessions
    
    def get_current_session(self) -> Optional[Dict[str, Any]]:
        """Get currently active charging session via /map-prod/v2 endpoint."""
        payload = {
            "user_status": {
                "mfhs": {}
            }
        }
        
        headers = {
            "accept": "*/*",
            "origin": "https://driver.chargepoint.com",
            "referer": "https://driver.chargepoint.com/",
            "x-requested-with": "XMLHttpRequest"
        }
        
        try:
            result = self._make_request(self.MAP_PROD_URL, payload, headers)
            
            # Extract current active session
            if isinstance(result, dict):
                # Look for active session indicators
                for key in ["active_session", "current_session", "session"]:
                    if key in result:
                        session = result[key]
                        if session:  # Not null/None
                            return session
                
                # Check user_status for active session
                if "user_status" in result and "session" in result["user_status"]:
                    return result["user_status"]["session"]
            
            return None
        except Exception as e:
            print(f"Error fetching current session: {e}")
            return None


if __name__ == "__main__":
    import sys
    
    username = os.getenv("CP_USERNAME")
    password = os.getenv("CP_PASSWORD")
    
    if not username or not password:
        print("ERROR: CP_USERNAME and CP_PASSWORD required")
        sys.exit(1)
    
    try:
        api = ChargePointDirectAPI(username, password)
        
        # Test: Get user sessions
        print("\n📊 Fetching user sessions...")
        sessions = api.get_user_sessions()
        if sessions:
            print(json.dumps(sessions, indent=2))
        
        # Test: Get current session
        print("\n⚡ Fetching current session...")
        current = api.get_current_session()
        if current:
            print(json.dumps(current, indent=2))
        else:
            print("No active session")
    
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
