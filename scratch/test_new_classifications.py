import urllib.request
import json

PORT = 8080
BASE_URL = f"http://127.0.0.1:{PORT}"

def test_new_types():
    print("Testing new publisher type and topic code ingest validation...")
    payload = {
        "source_name": "TechCrunch Science Africa",
        "platform": "newsletter",
        "ingest_url": "https://techcrunchafrica.substack.com",
        "primary_language": "en",
        "languages_spoken": "en",
        "geographic_focus": "Kenya",
        "publisher_type": "technology_science",
        "input_by": "andrew",
        "gating_passed": True,
        "activity_passed": True,
        "telegram_passed": False,
        "country_iso": "KE",
        "topic_code": "TEC"
    }
    
    req = urllib.request.Request(f"{BASE_URL}/api/sources", method="POST")
    req.add_header("Content-Type", "application/json")
    body = json.dumps(payload).encode("utf-8")
    
    try:
        with urllib.request.urlopen(req, data=body) as response:
            status_code = response.status
            content = response.read().decode("utf-8")
            resp_json = json.loads(content)
            print(f"Success! Status: {status_code}, Response: {resp_json}")
            assert status_code == 201
            assert resp_json["source_id"].startswith("KE_NEW_TEC_")
            print("Successfully validated new publisher type 'technology_science' and topic 'TEC'.")
    except Exception as e:
        if hasattr(e, "read"):
            err_content = e.read().decode("utf-8")
            print(f"Error: {e.code}, Content: {err_content}")
        else:
            print("Failed to run test:", e)

    print("Testing pr_news_agency publisher type ingest validation...")
    payload_pr = payload.copy()
    payload_pr["source_name"] = "African News Agency"
    payload_pr["ingest_url"] = "https://africanewsagency.com"
    payload_pr["publisher_type"] = "pr_news_agency"
    payload_pr["topic_code"] = "GEN"
    
    req_pr = urllib.request.Request(f"{BASE_URL}/api/sources", method="POST")
    req_pr.add_header("Content-Type", "application/json")
    body_pr = json.dumps(payload_pr).encode("utf-8")
    
    try:
        with urllib.request.urlopen(req_pr, data=body_pr) as response:
            status_code = response.status
            content = response.read().decode("utf-8")
            resp_json = json.loads(content)
            print(f"Success! Status: {status_code}, Response: {resp_json}")
            assert status_code == 201
            assert resp_json["source_id"].startswith("KE_NEW_GEN_")
            print("Successfully validated new publisher type 'pr_news_agency' and topic 'GEN'.")
    except Exception as e:
        if hasattr(e, "read"):
            err_content = e.read().decode("utf-8")
            print(f"Error: {e.code}, Content: {err_content}")
        else:
            print("Failed to run test:", e)

if __name__ == "__main__":
    test_new_types()
