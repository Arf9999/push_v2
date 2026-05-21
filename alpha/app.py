import os
import math
import httpx
import duckdb
import sqlite3
import hashlib
import secrets
from typing import List, Optional
from fastapi import FastAPI, Query, HTTPException, Header, Depends
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

USERS_DB_PATH = os.getenv("USERS_DB_PATH", "alpha/users.db")

def init_users_db():
    os.makedirs(os.path.dirname(USERS_DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(USERS_DB_PATH)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT UNIQUE PRIMARY KEY,
            password_hash TEXT,
            salt TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            search_text TEXT,
            space TEXT,
            searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS saved_searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            search_text TEXT,
            space TEXT,
            threshold REAL,
            latest_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            search_text TEXT,
            new_results_count INTEGER,
            newest_title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_read INTEGER DEFAULT 0
        );
    """)
    conn.commit()
    conn.close()

init_users_db()

def get_users_db_conn():
    conn = sqlite3.connect(USERS_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Password Helpers
def hash_password(password: str, salt: str = None) -> tuple:
    if salt is None:
        salt = secrets.token_hex(16)
    hash_obj = hashlib.sha256((password + salt).encode())
    return hash_obj.hexdigest(), salt

def verify_password(password: str, password_hash: str, salt: str) -> bool:
    h, _ = hash_password(password, salt)
    return h == password_hash

# Auth dependency
def get_current_user(authorization: Optional[str] = Header(None)) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication required")
    token = authorization
    if token.startswith("Bearer "):
        token = token[len("Bearer "):]
    username = token.strip()
    if not username:
        raise HTTPException(status_code=401, detail="Invalid authorization token")
    
    # Check user existence in sqlite
    conn = get_users_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=401, detail="Invalid user session")
    return username

app = FastAPI(
    title="Narrative Intelligence Engine API",
    description="Backend API for low-latency SQL-native vector search and narrative analytics."
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.getenv("DUCKDB_PATH", "alpha/newsletters.db")
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "openrouter").lower()
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ---------------------------------------------------------
# Vectorization Helper
# ---------------------------------------------------------
async def vectorize_query(query_text: str) -> List[float]:
    """
    Vectorizes search term by calling the configured embedding provider.
    """
    if not query_text:
        raise HTTPException(status_code=400, detail="Search query cannot be empty")
        
    async with httpx.AsyncClient(timeout=30.0) as client:
        if EMBEDDING_PROVIDER == "openrouter":
            # Fallback to OpenAI API format
            api_key = OPENROUTER_API_KEY if OPENROUTER_API_KEY else OPENAI_API_KEY
            if not api_key:
                raise HTTPException(status_code=500, detail="No API Key configured for OpenRouter/OpenAI embeddings")
            
            headers = {"Authorization": f"Bearer {api_key}"}
            body = {"model": EMBEDDING_MODEL, "input": query_text}
            
            resp = await client.post("https://api.openai.com/v1/embeddings", json=body, headers=headers)
            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail=f"Embedding provider error: {resp.text}")
            
            data = resp.json()
            return data["data"][0]["embedding"]
            
        elif EMBEDDING_PROVIDER == "openai":
            if not OPENAI_API_KEY:
                raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not configured")
                
            headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
            body = {"model": EMBEDDING_MODEL, "input": query_text}
            
            resp = await client.post("https://api.openai.com/v1/embeddings", json=body, headers=headers)
            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail=f"OpenAI error: {resp.text}")
                
            data = resp.json()
            return data["data"][0]["embedding"]
            
        elif EMBEDDING_PROVIDER == "ollama":
            url = f"{OLLAMA_HOST}/api/embed"
            body = {"model": EMBEDDING_MODEL, "input": query_text}
            
            resp = await client.post(url, json=body)
            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail=f"Ollama error: {resp.text}")
                
            data = resp.json()
            return data["embeddings"][0]
            
        elif EMBEDDING_PROVIDER == "gemini":
            if not GEMINI_API_KEY:
                raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not configured")
                
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{EMBEDDING_MODEL}:embedContent?key={GEMINI_API_KEY}"
            body = {"content": {"parts": [{"text": query_text}]}}
            
            resp = await client.post(url, json=body)
            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail=f"Gemini error: {resp.text}")
                
            data = resp.json()
            return data["embedding"]["values"]
            
        else:
            raise HTTPException(status_code=500, detail=f"Unsupported embedding provider: {EMBEDDING_PROVIDER}")

# ---------------------------------------------------------
# Database Utility Functions
# ---------------------------------------------------------
def get_db_con():
    """
    Opens connection to DuckDB database in read-only mode to prevent write locks. Caps resources.
    """
    if not os.path.exists(DB_PATH):
        # Create empty db file if it doesn't exist
        os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
        con = duckdb.connect(DB_PATH)
        con.close()
        
    con = duckdb.connect(DB_PATH, read_only=True)
    con.execute("SET max_memory = '512MB';")
    con.execute("SET threads = 1;")
    return con

# ---------------------------------------------------------
# API Pydantic Schemas
# ---------------------------------------------------------
class UserRegisterSchema(BaseModel):
    username: str
    password: str

class UserLoginSchema(BaseModel):
    username: str
    password: str

class HistoryCreateSchema(BaseModel):
    search_text: str
    space: str

class SavedSearchCreateSchema(BaseModel):
    search_text: str
    space: str
    threshold: float

# ---------------------------------------------------------
# API Routes
# ---------------------------------------------------------
@app.post("/api/auth/register")
async def register(schema: UserRegisterSchema):
    username = schema.username.strip()
    password = schema.password
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password cannot be empty")
        
    conn = get_users_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Username already exists")
        
    p_hash, salt = hash_password(password)
    try:
        cursor.execute(
            "INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
            (username, p_hash, salt)
        )
        conn.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")
    finally:
        conn.close()
        
    return {"message": "User registered successfully"}

@app.post("/api/auth/login")
async def login(schema: UserLoginSchema):
    username = schema.username.strip()
    password = schema.password
    
    conn = get_users_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash, salt FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=401, detail="Invalid username or password")
        
    p_hash = row["password_hash"]
    salt = row["salt"]
    
    if not verify_password(password, p_hash, salt):
        raise HTTPException(status_code=401, detail="Invalid username or password")
        
    return {"token": username, "username": username}

# History endpoints
@app.get("/api/history")
async def get_history(username: str = Depends(get_current_user)):
    conn = get_users_db_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, search_text, space, searched_at FROM search_history WHERE username = ? ORDER BY searched_at DESC LIMIT 10",
        (username,)
    )
    rows = cursor.fetchall()
    conn.close()
    
    history = []
    for r in rows:
        history.append({
            "id": r["id"],
            "search_text": r["search_text"],
            "space": r["space"],
            "searched_at": r["searched_at"]
        })
    return {"history": history}

@app.post("/api/history")
async def create_history(schema: HistoryCreateSchema, username: str = Depends(get_current_user)):
    conn = get_users_db_conn()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO search_history (username, search_text, space) VALUES (?, ?, ?)",
            (username, schema.search_text, schema.space)
        )
        conn.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to log history: {str(e)}")
    finally:
        conn.close()
    return {"message": "History logged successfully"}

# Saved Searches endpoints
@app.post("/api/saved-searches")
async def create_saved_search(schema: SavedSearchCreateSchema, username: str = Depends(get_current_user)):
    # 1. Query DuckDB to seed latest_id
    query_vector = await vectorize_query(schema.search_text)
    query_norm = math.sqrt(sum(x * x for x in query_vector))
    if query_norm == 0:
        query_norm = 1.0
        
    embedding_col = "english_embedding" if schema.space == "english" else "multilingual_embedding"
    
    con = get_db_con()
    latest_id = ""
    try:
        search_query = f"""
            SELECT 
                uid, 
                (list_dot_product({embedding_col}, ?) / (sqrt(list_dot_product({embedding_col}, {embedding_col})) * ?)) as similarity
            FROM newsletters
            WHERE {embedding_col} IS NOT NULL
            ORDER BY datetime DESC, similarity DESC;
        """
        results = con.execute(search_query, [query_vector, query_norm]).fetchall()
        for r in results:
            uid, sim = r[0], r[1]
            sim_val = float(sim) if sim is not None and not math.isnan(sim) else 0.0
            if sim_val >= schema.threshold:
                latest_id = uid
                break
    except Exception as e:
        latest_id = ""
    finally:
        con.close()
        
    # 2. Insert into SQLite
    conn = get_users_db_conn()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO saved_searches (username, search_text, space, threshold, latest_id) VALUES (?, ?, ?, ?, ?)",
            (username, schema.search_text, schema.space, schema.threshold, latest_id)
        )
        conn.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save search: {str(e)}")
    finally:
        conn.close()
        
    return {"message": "Search saved successfully", "latest_id": latest_id}

@app.get("/api/saved-searches")
async def get_saved_searches(username: str = Depends(get_current_user)):
    conn = get_users_db_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, search_text, space, threshold, latest_id, created_at FROM saved_searches WHERE username = ? ORDER BY created_at DESC",
        (username,)
    )
    rows = cursor.fetchall()
    conn.close()
    
    saved = []
    for r in rows:
        saved.append({
            "id": r["id"],
            "search_text": r["search_text"],
            "space": r["space"],
            "threshold": r["threshold"],
            "latest_id": r["latest_id"],
            "created_at": r["created_at"]
        })
    return {"saved_searches": saved}

@app.delete("/api/saved-searches/{saved_search_id}")
async def delete_saved_search(saved_search_id: int, username: str = Depends(get_current_user)):
    conn = get_users_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM saved_searches WHERE id = ?", (saved_search_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Saved search not found")
        
    if row["username"] != username:
        conn.close()
        raise HTTPException(status_code=403, detail="Not authorized to delete this saved search")
        
    try:
        cursor.execute("DELETE FROM saved_searches WHERE id = ?", (saved_search_id,))
        conn.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete saved search: {str(e)}")
    finally:
        conn.close()
        
    return {"message": "Saved search deleted successfully"}

# Notifications endpoints
@app.get("/api/notifications")
async def get_notifications(username: str = Depends(get_current_user)):
    conn = get_users_db_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, search_text, new_results_count, newest_title, created_at, is_read FROM notifications WHERE username = ? ORDER BY created_at DESC",
        (username,)
    )
    rows = cursor.fetchall()
    conn.close()
    
    notifications = []
    for r in rows:
        notifications.append({
            "id": r["id"],
            "search_text": r["search_text"],
            "new_results_count": r["new_results_count"],
            "newest_title": r["newest_title"],
            "created_at": r["created_at"],
            "is_read": bool(r["is_read"])
        })
    return {"notifications": notifications}

@app.post("/api/notifications/read")
async def mark_notifications_read(username: str = Depends(get_current_user)):
    conn = get_users_db_conn()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE notifications SET is_read = 1 WHERE username = ?",
            (username,)
        )
        conn.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update notifications: {str(e)}")
    finally:
        conn.close()
        
    return {"message": "Notifications marked as read"}

@app.post("/api/notifications/check")
async def check_notifications(username: str = Depends(get_current_user)):
    # Batch check can be triggered by any authenticated user for testing simulation
    conn = get_users_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, search_text, space, threshold, latest_id FROM saved_searches")
    saved_searches = cursor.fetchall()
    
    con = get_db_con()
    try:
        for s in saved_searches:
            s_id = s["id"]
            user = s["username"]
            search_text = s["search_text"]
            space = s["space"]
            threshold = s["threshold"]
            latest_id = s["latest_id"]
            
            latest_datetime = "1970-01-01 00:00:00"
            if latest_id:
                try:
                    dt_res = con.execute("SELECT datetime::VARCHAR FROM newsletters WHERE uid = ?", [latest_id]).fetchone()
                    if dt_res:
                        latest_datetime = dt_res[0]
                except Exception:
                    pass
            
            query_vector = await vectorize_query(search_text)
            query_norm = math.sqrt(sum(x * x for x in query_vector))
            if query_norm == 0:
                query_norm = 1.0
                
            embedding_col = "english_embedding" if space == "english" else "multilingual_embedding"
            
            search_query = f"""
                SELECT 
                    uid, 
                    title,
                    datetime::VARCHAR as datetime,
                    (list_dot_product({embedding_col}, ?) / (sqrt(list_dot_product({embedding_col}, {embedding_col})) * ?)) as similarity
                FROM newsletters
                WHERE {embedding_col} IS NOT NULL AND datetime > ?
                ORDER BY datetime DESC, similarity DESC;
            """
            
            results = con.execute(search_query, [query_vector, query_norm, latest_datetime]).fetchall()
            
            new_matches = []
            for r in results:
                uid, title, dt, sim = r
                sim_val = float(sim) if sim is not None and not math.isnan(sim) else 0.0
                if sim_val >= threshold:
                    new_matches.append({"uid": uid, "title": title, "datetime": dt})
                    
            if new_matches:
                newest_article = new_matches[0]
                new_results_count = len(new_matches)
                newest_title = newest_article["title"]
                new_latest_id = newest_article["uid"]
                
                cursor.execute(
                    """
                    INSERT INTO notifications (username, search_text, new_results_count, newest_title)
                    VALUES (?, ?, ?, ?)
                    """,
                    (user, search_text, new_results_count, newest_title)
                )
                
                cursor.execute(
                    "UPDATE saved_searches SET latest_id = ? WHERE id = ?",
                    (new_latest_id, s_id)
                )
                
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Batch check failed: {str(e)}")
    finally:
        con.close()
        conn.close()
        
    return {"message": "Notifications check completed"}

# ---------------------------------------------------------
# API Routes
# ---------------------------------------------------------
@app.get("/")
async def root():
    """Redirect to static index dashboard"""
    return RedirectResponse(url="/static/index.html")

@app.get("/api/search")
async def search_newsletters(
    q: str = Query(..., description="Query terms to search"),
    space: str = Query("english", regex="^(english|multilingual)$"),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Endpoint for SQL-native vector similarity search using list_dot_product.
    """
    # 1. Vectorize query string
    query_vector = await vectorize_query(q)
    
    # Compute L2 Norm of query vector: sqrt(sum(x^2))
    query_norm = math.sqrt(sum(x * x for x in query_vector))
    if query_norm == 0:
        query_norm = 1.0
        
    embedding_col = "english_embedding" if space == "english" else "multilingual_embedding"
    
    # 2. Run query in DuckDB
    con = get_db_con()
    try:
        # We pass query_vector directly as a DuckDB parameter. DuckDB Python maps lists to ARRAY/LIST types.
        # Calculation: list_dot_product(col, query) / (sqrt(list_dot_product(col, col)) * query_norm)
        search_query = f"""
            SELECT 
                uid, 
                datetime::VARCHAR as datetime, 
                source, 
                sender, 
                title, 
                summary, 
                original_language_summary, 
                detected_language, 
                content_type, 
                topics, 
                themes, 
                keywords,
                (list_dot_product({embedding_col}, ?) / (sqrt(list_dot_product({embedding_col}, {embedding_col})) * ?)) as similarity,
                (SELECT string_agg(canonical_name || ':' || entity_type, ';') FROM entities WHERE entities.uid = newsletters.uid) as entity_list
            FROM newsletters
            WHERE {embedding_col} IS NOT NULL
            ORDER BY similarity DESC
            LIMIT ?;
        """
        
        results = con.execute(search_query, [query_vector, query_norm, limit]).fetchall()
        
        newsletters = []
        for r in results:
            entities = []
            if r[13]:
                for ent_str in r[13].split(";"):
                    if ":" in ent_str:
                        name, etype = ent_str.split(":", 1)
                        entities.append({"name": name, "type": etype})
            
            newsletters.append({
                "uid": r[0],
                "datetime": r[1],
                "source": r[2],
                "sender": r[3],
                "title": r[4],
                "summary": r[5],
                "original_language_summary": r[6],
                "detected_language": r[7],
                "content_type": r[8],
                "topics": [t.strip() for t in r[9].split(",")] if r[9] else [],
                "themes": [t.strip() for t in r[10].split(",")] if r[10] else [],
                "keywords": [t.strip() for t in r[11].split(",")] if r[11] else [],
                "similarity": float(r[12]) if r[12] is not None and not math.isnan(r[12]) else 0.0,
                "entities": entities
            })
            
        return {"query": q, "space": space, "results": newsletters}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
    finally:
        con.close()

@app.get("/api/stats")
async def get_stats():
    """
    Analytics endpoint returning high-level metrics for dashboard graphs.
    """
    con = get_db_con()
    try:
        total_articles = con.execute("SELECT COUNT(*) FROM newsletters;").fetchone()[0]
        
        lang_res = con.execute("""
            SELECT detected_language, COUNT(*) as count 
            FROM newsletters 
            GROUP BY detected_language 
            ORDER BY count DESC;
        """).fetchall()
        languages = [{"lang": r[0], "count": r[1]} for r in lang_res]
        
        source_res = con.execute("""
            SELECT source, COUNT(*) as count 
            FROM newsletters 
            GROUP BY source 
            ORDER BY count DESC 
            LIMIT 10;
        """).fetchall()
        sources = [{"source": r[0], "count": r[1]} for r in source_res]
        
        entity_res = con.execute("""
            SELECT canonical_name, entity_type, COUNT(*) as count 
            FROM entities 
            GROUP BY canonical_name, entity_type 
            ORDER BY count DESC 
            LIMIT 10;
        """).fetchall()
        top_entities = [{"name": r[0], "type": r[1], "count": r[2]} for r in entity_res]
        
        marketing_res = con.execute("""
            SELECT COUNT(*) FROM newsletters WHERE subscription_marketing = true;
        """).fetchone()[0]
        
        return {
            "total_articles": total_articles,
            "languages": languages,
            "sources": sources,
            "top_entities": top_entities,
            "marketing_count": marketing_res
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch database metrics: {str(e)}")
    finally:
        con.close()

@app.get("/api/entities")
async def get_entities():
    """
    Fetch all canonical entities mapped to their raw aliases.
    """
    con = get_db_con()
    try:
        # Group raw aliases per canonical name
        entity_rows = con.execute("""
            SELECT canonical_name, entity_type, LIST(DISTINCT raw_name) as aliases, COUNT(*) as count
            FROM entities
            GROUP BY canonical_name, entity_type
            ORDER BY count DESC;
        """).fetchall()
        
        entities_list = []
        for r in entity_rows:
            entities_list.append({
                "canonical_name": r[0],
                "type": r[1],
                "aliases": r[2],
                "occurrence_count": r[3]
            })
            
        return {"entities": entities_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch entity mappings: {str(e)}")
    finally:
        con.close()

# ---------------------------------------------------------
# Static File Mount
# ---------------------------------------------------------
# Create empty static folder if not exists
os.makedirs("alpha/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="alpha/static"), name="static")
