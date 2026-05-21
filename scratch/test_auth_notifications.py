import os
import sys
import unittest
import math
import shutil
import sqlite3
import duckdb
from fastapi.testclient import TestClient

# 1. Set environment variables BEFORE importing app to force isolation
TEST_USERS_DB = "scratch/test_users.db"
TEST_DUCKDB = "scratch/test_newsletters.db"

os.environ["USERS_DB_PATH"] = TEST_USERS_DB
os.environ["DUCKDB_PATH"] = TEST_DUCKDB

# Add project root to path to ensure alpha module imports correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from alpha.app import app, get_users_db_conn
import alpha.app

# 2. Mock vectorize_query to avoid external API dependencies
async def mock_vectorize_query(query_text: str):
    # Return a dummy 3-dimensional vector (or larger if needed)
    # Let's return a 384-dimensional vector since nomic-embed-text is 384/768
    return [0.5] * 384

alpha.app.vectorize_query = mock_vectorize_query

class TestAuthNotifications(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Ensure scratch dir exists
        os.makedirs("scratch", exist_ok=True)
        
        # Clean up any leftover test databases
        for path in [TEST_USERS_DB, TEST_DUCKDB]:
            if os.path.exists(path):
                try:
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                except Exception:
                    pass
        
        # Setup mock DuckDB newsletter and entities tables
        cls.db_con = duckdb.connect(TEST_DUCKDB)
        cls.db_con.execute("""
            CREATE TABLE newsletters (
                uid VARCHAR PRIMARY KEY,
                datetime TIMESTAMP,
                source VARCHAR,
                sender VARCHAR,
                title VARCHAR,
                url VARCHAR,
                summary TEXT,
                original_language_summary TEXT,
                detected_language VARCHAR,
                truncated BOOLEAN,
                content_type VARCHAR,
                topics TEXT,
                themes TEXT,
                keywords TEXT,
                subscription_marketing BOOLEAN,
                english_embedding FLOAT[],
                multilingual_embedding FLOAT[],
                ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        cls.db_con.execute("""
            CREATE SEQUENCE entity_id_seq;
            CREATE TABLE entities (
                entity_id INTEGER DEFAULT nextval('entity_id_seq') PRIMARY KEY,
                uid VARCHAR,
                entity_type VARCHAR,
                raw_name VARCHAR,
                canonical_name VARCHAR
            );
        """)
        
        # Seed initial test articles in DuckDB
        # We use a mock vector [0.5] * 384 (which normalizes to length 1.0 approx)
        # L2 norm: sqrt(sum(0.5^2 for i in range(384))) = sqrt(384 * 0.25) = sqrt(96) = 9.797959
        # To make dot product similarity simple:
        # dot_product(v1, v2) = sum(0.5 * 0.5) = 384 * 0.25 = 96.
        # similarity = 96 / (sqrt(96) * sqrt(96)) = 1.0!
        mock_embedding = [0.5] * 384
        
        cls.db_con.execute(
            """
            INSERT INTO newsletters (
                uid, datetime, source, sender, title, url, summary, 
                original_language_summary, detected_language, truncated, 
                content_type, topics, themes, keywords, subscription_marketing, 
                english_embedding, multilingual_embedding
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "uid-1", "2026-05-20 10:00:00", "RSS", "Editor", "Initial Energy Policies", 
                "http://example.com/1", "A summary about energy policies.", 
                "Original summary.", "en", False, "Article", "energy, policies", 
                "governance", "security", False, mock_embedding, mock_embedding
            )
        )
        
        cls.db_con.execute(
            "INSERT INTO entities (uid, entity_type, raw_name, canonical_name) VALUES (?, ?, ?, ?)",
            ("uid-1", "ORG", "Eskom Holdings", "Eskom")
        )
        
        # Close connection to allow app.py to connect in read-only mode
        cls.db_con.close()
        
        # Initialize SQLite users database
        alpha.app.init_users_db()
        
        cls.client = TestClient(app)
        cls.username = "testuser"
        cls.password = "securepass123"
        cls.token = None

    @classmethod
    def tearDownClass(cls):
        # Clean up databases
        for path in [TEST_USERS_DB, TEST_DUCKDB]:
            if os.path.exists(path):
                try:
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                except Exception:
                    pass

    def test_01_registration(self):
        # Fail with empty username/password
        resp = self.client.post("/api/auth/register", json={"username": "", "password": ""})
        self.assertEqual(resp.status_code, 400)
        
        # Success registration
        resp = self.client.post("/api/auth/register", json={
            "username": self.username,
            "password": self.password
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["message"], "User registered successfully")
        
        # Fail duplicate registration
        resp = self.client.post("/api/auth/register", json={
            "username": self.username,
            "password": self.password
        })
        self.assertEqual(resp.status_code, 400)
        self.assertIn("already exists", resp.json()["detail"])

    def test_02_login(self):
        # Fail with wrong password
        resp = self.client.post("/api/auth/login", json={
            "username": self.username,
            "password": "wrongpassword"
        })
        self.assertEqual(resp.status_code, 401)
        
        # Success login
        resp = self.client.post("/api/auth/login", json={
            "username": self.username,
            "password": self.password
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("token", data)
        self.assertEqual(data["username"], self.username)
        
        # Store token for subsequent tests
        type(self).token = data["token"]

    def test_03_search_history(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Log search history
        resp = self.client.post("/api/history", json={
            "search_text": "energy security",
            "space": "english"
        }, headers=headers)
        self.assertEqual(resp.status_code, 200)
        
        # Retrieve search history
        resp = self.client.get("/api/history", headers=headers)
        self.assertEqual(resp.status_code, 200)
        history = resp.json()["history"]
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["search_text"], "energy security")
        self.assertEqual(history[0]["space"], "english")

    def test_04_saved_searches(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Save search query
        resp = self.client.post("/api/saved-searches", json={
            "search_text": "energy security",
            "space": "english",
            "threshold": 0.40
        }, headers=headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["latest_id"], "uid-1") # seeded from initial article in DuckDB
        
        # Fetch saved searches
        resp = self.client.get("/api/saved-searches", headers=headers)
        self.assertEqual(resp.status_code, 200)
        saved = resp.json()["saved_searches"]
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["search_text"], "energy security")
        self.assertEqual(saved[0]["space"], "english")
        self.assertEqual(saved[0]["threshold"], 0.40)
        self.assertEqual(saved[0]["latest_id"], "uid-1")
        
        saved_id = saved[0]["id"]
        
        # Verify deletion works on a mock query
        resp = self.client.post("/api/saved-searches", json={
            "search_text": "temp search",
            "space": "english",
            "threshold": 0.50
        }, headers=headers)
        temp_id = resp.json().get("latest_id") # doesn't matter, we want id from list
        
        resp = self.client.get("/api/saved-searches", headers=headers)
        temp_search_record = [s for s in resp.json()["saved_searches"] if s["search_text"] == "temp search"][0]
        
        # Delete temp search
        resp = self.client.delete(f"/api/saved-searches/{temp_search_record['id']}", headers=headers)
        self.assertEqual(resp.status_code, 200)
        
        # Verify it's gone
        resp = self.client.get("/api/saved-searches", headers=headers)
        saved_after = resp.json()["saved_searches"]
        self.assertEqual(len(saved_after), 1)
        self.assertEqual(saved_after[0]["id"], saved_id)

    def test_05_notifications_and_cron_simulation(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # 1. Verify no notifications initially
        resp = self.client.get("/api/notifications", headers=headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["notifications"]), 0)
        
        # 2. Run batch check simulation (nothing new should be found because no new article was added)
        resp = self.client.post("/api/notifications/check", headers=headers)
        self.assertEqual(resp.status_code, 200)
        
        resp = self.client.get("/api/notifications", headers=headers)
        self.assertEqual(len(resp.json()["notifications"]), 0)
        
        # 3. Inject a new article in DuckDB with a higher datetime (simulating new ingestion)
        # Note: we need to reopen DuckDB connection in write mode
        db_con = duckdb.connect(TEST_DUCKDB)
        mock_embedding = [0.5] * 384
        db_con.execute(
            """
            INSERT INTO newsletters (
                uid, datetime, source, sender, title, url, summary, 
                original_language_summary, detected_language, truncated, 
                content_type, topics, themes, keywords, subscription_marketing, 
                english_embedding, multilingual_embedding
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "uid-2", "2026-05-21 12:00:00", "RSS", "Editor", "New Energy security Breakthrough", 
                "http://example.com/2", "A newer summary about energy breakthroughs.", 
                "Original summary 2.", "en", False, "Article", "energy, security", 
                "governance", "security", False, mock_embedding, mock_embedding
            )
        )
        db_con.close()
        
        # 4. Trigger notification check again
        resp = self.client.post("/api/notifications/check", headers=headers)
        self.assertEqual(resp.status_code, 200)
        
        # 5. Verify notification was created
        resp = self.client.get("/api/notifications", headers=headers)
        self.assertEqual(resp.status_code, 200)
        notifications = resp.json()["notifications"]
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["search_text"], "energy security")
        self.assertEqual(notifications[0]["new_results_count"], 1)
        self.assertEqual(notifications[0]["newest_title"], "New Energy security Breakthrough")
        self.assertEqual(notifications[0]["is_read"], False)
        
        # 6. Verify saved_searches latest_id updated to uid-2
        resp = self.client.get("/api/saved-searches", headers=headers)
        saved = resp.json()["saved_searches"]
        self.assertEqual(saved[0]["latest_id"], "uid-2")
        
        # 7. Mark notifications as read
        resp = self.client.post("/api/notifications/read", headers=headers)
        self.assertEqual(resp.status_code, 200)
        
        # Verify read state
        resp = self.client.get("/api/notifications", headers=headers)
        self.assertEqual(resp.json()["notifications"][0]["is_read"], True)

if __name__ == "__main__":
    unittest.main()
