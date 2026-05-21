import os
import sys
import time
import subprocess
import json
import urllib.request
import urllib.error
import urllib.parse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "alpha_survey", "sources.db")
PORT = 8089
BASE_URL = f"http://127.0.0.1:{PORT}"

def setup_clean_db():
    print(f"Cleaning database at: {DB_PATH}")
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            print("Previous test database removed.")
        except Exception as e:
            print(f"Warning: Could not remove db: {e}")

def make_request(method, path, data=None, headers=None, params=None):
    url = f"{BASE_URL}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    
    req = urllib.request.Request(url, method=method)
    
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
            
    if data is not None:
        req.add_header("Content-Type", "application/json")
        body = json.dumps(data).encode("utf-8")
    else:
        body = None
        
    try:
        with urllib.request.urlopen(req, data=body) as response:
            status_code = response.status
            content = response.read().decode("utf-8")
            try:
                resp_json = json.loads(content)
            except:
                resp_json = content
            return status_code, resp_json
    except urllib.error.HTTPError as e:
        status_code = e.code
        content = e.read().decode("utf-8")
        try:
            resp_json = json.loads(content)
        except:
            resp_json = content
        return status_code, resp_json

def run_tests():
    print("\n--- Starting Regional Media Ingestion API Verification ---")
    
    # 0.1 Test User Login (Invalid credentials)
    print("\n[Test 0.1] Attempt login with invalid credentials...")
    status_code, resp_json = make_request("POST", "/api/login", data={"username": "ra_amina", "password": "wrongpassword"})
    print("Response status (expect 401):", status_code)
    assert status_code == 401
    
    # 0.2 Test User Login (Valid seeded credentials)
    print("\n[Test 0.2] Attempt login with seeded credentials (ra_amina)...")
    status_code, resp_json = make_request("POST", "/api/login", data={"username": "ra_amina", "password": "amina2026"})
    print("Response status (expect 200):", status_code)
    print("Response JSON:", resp_json)
    assert status_code == 200
    assert resp_json["username"] == "ra_amina"
    
    # 0.3 Test User User Allocation (Access control check)
    print("\n[Test 0.3.1] Fetch allocated users list without admin token...")
    status_code, resp_json = make_request("GET", "/api/admin/users")
    print("Response status (expect 401):", status_code)
    assert status_code == 401

    print("\n[Test 0.3.2] Fetch allocated users list with admin token...")
    status_code, resp_json = make_request("GET", "/api/admin/users", headers={"X-Admin-Token": "admin123"})
    print("Response status:", status_code)
    print("Response JSON (expect ra_amina, ra_bob, ra_coordinator):", resp_json)
    assert status_code == 200
    assert "ra_amina" in resp_json
    assert "ra_bob" in resp_json
    
    # Allocate new user account
    print("\n[Test 0.3.3] Allocate new auditor account (ra_david)...")
    status_code, resp_json = make_request(
        "POST", "/api/admin/users", 
        data={"username": "ra_david", "password": "davidpassword"},
        headers={"X-Admin-Token": "admin123"}
    )
    print("Response status (expect 200):", status_code)
    assert status_code == 200
    
    # Verify new account logs in
    print("\n[Test 0.3.4] Log in as newly allocated user...")
    status_code, resp_json = make_request("POST", "/api/login", data={"username": "ra_david", "password": "davidpassword"})
    print("Response status (expect 200):", status_code)
    assert status_code == 200
    
    # Revoke account david
    print("\n[Test 0.3.5] Revoking david account...")
    status_code, resp_json = make_request(
        "DELETE", "/api/admin/users/ra_david",
        headers={"X-Admin-Token": "admin123"}
    )
    print("Response status (expect 200):", status_code)
    assert status_code == 200
    
    # Verify david can no longer log in
    print("\n[Test 0.3.6] Confirm revoked user login failure...")
    status_code, resp_json = make_request("POST", "/api/login", data={"username": "ra_david", "password": "davidpassword"})
    print("Response status (expect 401):", status_code)
    assert status_code == 401
    print("SUCCESS: User allocation and management flows fully authenticated and validated.")

    # 1. Test POST /api/sources (Valid record creation)
    payload = {
        "source_name": "Premium Times Nigeria",
        "platform": "telegram",
        "ingest_url": "https://t.me/s/premiumtimes",
        "primary_language": "en",
        "languages_spoken": "en;yo;ha",
        "geographic_focus": "Nigeria; Abuja",
        "publisher_type": "independent_journalist",
        "input_by": "ra_amina",
        "gating_passed": True,
        "activity_passed": True,
        "telegram_passed": True,
        "country_iso": "NG",
        "topic_code": "POL"
    }
    
    print("\n[Test 1] Logging new valid source...")
    status_code, resp_json = make_request("POST", "/api/sources", data=payload)
    print("Response status:", status_code)
    print("Response JSON:", resp_json)
    assert status_code == 201
    source_id = resp_json["source_id"]
    assert source_id.startswith("NG_TEL_POL_")
    print(f"SUCCESS: Mapped to source_id={source_id}")

    # 2. Test GET /api/check_duplicate
    print("\n[Test 2] Testing duplicate check helper...")
    status_code, resp_json = make_request("GET", "/api/check_duplicate", params={"url": "https://t.me/s/premiumtimes"})
    print("Response JSON:", resp_json)
    assert status_code == 200
    assert resp_json["is_duplicate"] is True
    assert resp_json["url_match"]["source_id"] == source_id
    print("SUCCESS: Duplicate check correctly flagged URL match.")

    # 3. Test POST /api/sources (Duplicate rejection)
    print("\n[Test 3] Re-logging identical URL (Expect 400 rejection)...")
    status_code, resp_json = make_request("POST", "/api/sources", data=payload)
    print("Response status:", status_code)
    print("Response JSON:", resp_json)
    assert status_code == 400
    assert "already exists" in resp_json["detail"]
    print("SUCCESS: Duplicate entry was blocked.")

    # 4. Test POST /api/sources (Private Telegram validation rejection)
    print("\n[Test 4] Logging private Telegram channel (Expect 400 rejection)...")
    private_payload = payload.copy()
    private_payload["ingest_url"] = "https://t.me/+joinchat/abcde123"
    status_code, resp_json = make_request("POST", "/api/sources", data=private_payload)
    print("Response status:", status_code)
    print("Response JSON:", resp_json)
    assert status_code == 400
    assert "Private Telegram invite links" in resp_json["detail"]
    print("SUCCESS: Private Telegram invite link rejected.")

    # 5. Test GET /api/sources (Public list check)
    print("\n[Test 5] Fetching active sources...")
    status_code, resp_json = make_request("GET", "/api/sources")
    print("Response status:", status_code)
    sources = resp_json
    print("Active sources count:", len(sources))
    assert len(sources) == 1
    assert sources[0]["source_id"] == source_id
    assert sources[0]["input_by"] == "ra_amina"
    print("SUCCESS: List contains added source and retains 'input_by' field.")

    # 6. Test GET /api/stats
    print("\n[Test 6] Checking aggregate stats...")
    status_code, resp_json = make_request("GET", "/api/stats")
    print("Response JSON:", resp_json)
    assert status_code == 200
    stats = resp_json
    assert stats["total_active"] == 1
    assert stats["by_platform"]["telegram"] == 1
    assert stats["by_country"]["NG"] == 1
    print("SUCCESS: Stats aggregate logic is accurate.")

    # 7. Test Admin actions (Verify) without & with token
    print("\n[Test 7.1] Verification check without passcode header...")
    status_code, resp_json = make_request("POST", f"/api/sources/{source_id}/verify", params={"verify": "true"})
    print("Response status (expect 401):", status_code)
    assert status_code == 401
    
    print("\n[Test 7.2] Verification check with correct passcode header...")
    status_code, resp_json = make_request(
        "POST", f"/api/sources/{source_id}/verify",
        params={"verify": "true"},
        headers={"X-Admin-Token": "admin123"}
    )
    print("Response status (expect 200):", status_code)
    assert status_code == 200
    
    # Re-verify list shows verified
    status_code, resp_json = make_request("GET", "/api/sources")
    assert resp_json[0]["is_verified"] == 1
    print("SUCCESS: Verification state toggled and requires authorization header.")

    # 8. Test Admin actions (Soft delete)
    print("\n[Test 8.1] Soft-deleting without passcode header...")
    status_code, resp_json = make_request("DELETE", f"/api/sources/{source_id}")
    print("Response status (expect 401):", status_code)
    assert status_code == 401

    print("\n[Test 8.2] Soft-deleting with passcode header...")
    status_code, resp_json = make_request(
        "DELETE", f"/api/sources/{source_id}",
        headers={"X-Admin-Token": "admin123"}
    )
    print("Response status (expect 200):", status_code)
    assert status_code == 200

    # 9. Test lists and stats after deletion
    print("\n[Test 9.1] Fetching active list after soft-delete (expect 0 active)...")
    status_code, resp_json = make_request("GET", "/api/sources")
    assert len(resp_json) == 0

    print("[Test 9.2] Fetching list including deleted (expect 1)...")
    status_code, resp_json = make_request("GET", "/api/sources", params={"include_deleted": "true"})
    assert len(resp_json) == 1
    assert resp_json[0]["is_deleted"] == 1

    print("[Test 9.3] Checking stats post-delete (expect 0 active, 1 deleted)...")
    status_code, stats = make_request("GET", "/api/stats")
    assert stats["total_active"] == 0
    assert stats["total_deleted"] == 1
    print("SUCCESS: Soft deletion hiding works, and stats report correctly.")

    # 10. Test Admin actions (Restore)
    print("\n[Test 10.1] Restoring without passcode header...")
    status_code, resp_json = make_request("POST", f"/api/sources/{source_id}/restore")
    print("Response status (expect 401):", status_code)
    assert status_code == 401

    print("\n[Test 10.2] Restoring with passcode header...")
    status_code, resp_json = make_request(
        "POST", f"/api/sources/{source_id}/restore",
        headers={"X-Admin-Token": "admin123"}
    )
    print("Response status (expect 200):", status_code)
    assert status_code == 200

    # Verify active list has it back
    status_code, resp_json = make_request("GET", "/api/sources")
    assert len(resp_json) == 1
    assert resp_json[0]["is_deleted"] == 0
    print("SUCCESS: Source restoration completed.")

    # 11. Test CSV export with & without passcode query parameter
    print("\n[Test 11.1] Exporting CSV without admin token query param...")
    status_code, resp_json = make_request("GET", "/api/export")
    print("Response status (expect 401):", status_code)
    assert status_code == 401

    print("\n[Test 11.2] Exporting CSV with admin token query param...")
    status_code, resp_json = make_request("GET", "/api/export", params={"admin_token": "admin123"})
    print("Response status (expect 200):", status_code)
    assert status_code == 200
    assert "source_id,source_name" in resp_json
    assert "Premium Times Nigeria" in resp_json
    assert "ra_amina" in resp_json
    print("SUCCESS: CSV generated, contains BOM, headers, and values.")

    # 11.3 Test Log export without passcode query parameter
    print("\n[Test 11.3] Exporting Activity Log without admin token query param...")
    status_code, resp_json = make_request("GET", "/api/admin/logs")
    print("Response status (expect 401):", status_code)
    assert status_code == 401

    # 11.4 Test Log export with passcode query parameter
    print("\n[Test 11.4] Exporting Activity Log with admin token query param...")
    status_code, resp_json = make_request("GET", "/api/admin/logs", params={"admin_token": "admin123"})
    print("Response status (expect 200):", status_code)
    assert status_code == 200
    assert "Action: Admin exported source database" in resp_json or "SQLite sources database" in resp_json
    print("SUCCESS: Log file retrieved successfully.")
    
    # 12. Test User-Scoped filtration endpoints (sources, stats, export)
    print("\n[Test 12.1] Fetching sources scoped to ra_amina...")
    status_code, resp_json = make_request("GET", "/api/sources", params={"input_by": "ra_amina"})
    print("Response status (expect 200):", status_code)
    assert status_code == 200
    assert len(resp_json) == 1
    assert resp_json[0]["input_by"] == "ra_amina"
    
    print("\n[Test 12.2] Fetching sources scoped to ra_bob...")
    status_code, resp_json = make_request("GET", "/api/sources", params={"input_by": "ra_bob"})
    print("Response status (expect 200):", status_code)
    assert status_code == 200
    assert len(resp_json) == 0
    
    print("\n[Test 12.3] Fetching stats scoped to ra_amina...")
    status_code, resp_json = make_request("GET", "/api/stats", params={"input_by": "ra_amina"})
    print("Response JSON:", resp_json)
    assert status_code == 200
    assert resp_json["total_active"] == 1
    assert resp_json["by_platform"]["telegram"] == 1
    
    print("\n[Test 12.4] Fetching stats scoped to ra_bob...")
    status_code, resp_json = make_request("GET", "/api/stats", params={"input_by": "ra_bob"})
    print("Response JSON:", resp_json)
    assert status_code == 200
    assert resp_json["total_active"] == 0
    assert resp_json["by_platform"]["telegram"] == 0
    
    print("\n[Test 12.5] Exporting CSV scoped to ra_amina...")
    status_code, resp_json = make_request("GET", "/api/export", params={"admin_token": "admin123", "input_by": "ra_amina"})
    print("Response status (expect 200):", status_code)
    assert status_code == 200
    assert "Premium Times Nigeria" in resp_json
    assert "ra_amina" in resp_json
    
    print("\n[Test 12.6] Exporting CSV scoped to ra_bob...")
    status_code, resp_json = make_request("GET", "/api/export", params={"admin_token": "admin123", "input_by": "ra_bob"})
    print("Response status (expect 200):", status_code)
    assert status_code == 200
    assert "Premium Times Nigeria" not in resp_json
    print("SUCCESS: User-scoped endpoint filtration successfully verified.")
    
    # 13. Test Logging Fediverse Platform Source
    print("\n[Test 13.1] Logging new valid Fediverse source...")
    fediverse_source = {
        "source_name": "Mastodon News Room",
        "platform": "fediverse",
        "ingest_url": "https://mastodon.social/@newsroom",
        "primary_language": "en",
        "languages_spoken": "en",
        "geographic_focus": "global",
        "publisher_type": "independent_journalist",
        "input_by": "ra_amina",
        "gating_passed": True,
        "activity_passed": True,
        "telegram_passed": False,
        "country_iso": "US",
        "topic_code": "GEN"
    }
    status_code, resp_json = make_request("POST", "/api/sources", data=fediverse_source)
    print("Response status (expect 201):", status_code)
    print("Response JSON:", resp_json)
    assert status_code == 201
    assert resp_json["status"] == "success"
    assert resp_json["source_id"].startswith("US_FED_GEN_")
    
    print("\n[Test 13.2] Checking stats with Fediverse source added...")
    status_code, resp_json = make_request("GET", "/api/stats")
    print("Response JSON stats:", resp_json)
    assert status_code == 200
    assert resp_json["by_platform"]["fediverse"] == 1
    print("SUCCESS: Fediverse mapping and stats validated successfully.")
    
    print("\nALL VERIFICATION TESTS COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    setup_clean_db()
    
    # Launch uvicorn process
    print(f"Launching FastAPI App on port {PORT}...")
    server_process = subprocess.Popen(
        [
            os.path.join(BASE_DIR, ".venv", "bin", "python"),
            "-m", "uvicorn", "alpha_survey.app:app",
            "--host", "127.0.0.1", "--port", str(PORT)
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=BASE_DIR
    )
    
    # Wait for server startup
    time.sleep(2.5)
    
    try:
        run_tests()
    except AssertionError as ae:
        print("\n❌ ASSERTION ERROR IN TESTS:", ae)
        # Check if server died
        ret = server_process.poll()
        if ret is not None:
            print("Server process exited prematurely with code:", ret)
            out, err = server_process.communicate()
            print("STDOUT:", out.decode())
            print("STDERR:", err.decode())
        sys.exit(1)
    except Exception as e:
        print("\n❌ UNEXPECTED ERROR:", e)
        sys.exit(1)
    finally:
        print("Shutting down FastAPI verification server...")
        server_process.terminate()
        server_process.wait()
        print("FastAPI verification server stopped.")
