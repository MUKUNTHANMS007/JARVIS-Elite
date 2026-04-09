import hmac
import hashlib
import requests
import json
import time

# J.A.R.V.I.S. Neural Sentinel (Local Mock Trigger)
# Simulation of a Cloudflare Worker notifying the Core API.

SECRET = "J_SENTINEL_SECURE_2026"
CORE_URL = "http://localhost:8000/api/neural/edge-trigger"

payload = {
    "type": "PROACTIVE_TRIGGER",
    "event_id": "test_meeting_123",
    "title": "Strategy Board Meeting (Urgent)",
    "timestamp": int(time.time())
}

payload_json = json.dumps(payload).encode()
signature = hmac.new(SECRET.encode(), payload_json, hashlib.sha256).hexdigest()

headers = {
    "Content-Type": "application/json",
    "X-Neural-Signature": signature
}

try:
    print(f"[Sentinel Mock] Dispatching trigger: {payload['title']}...")
    response = requests.post(CORE_URL, data=payload_json, headers=headers)
    
    if response.status_code == 200:
        print("[Sentinel Mock] SUCCESS: Trigger injected into Neural Core.")
        print(f"Response: {response.json()}")
    else:
        print(f"[Sentinel Mock] FAIL: Received status {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"[Sentinel Mock] ERROR: {e}")
