import os
import math
import httpx
import duckdb
from typing import List, Optional
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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
