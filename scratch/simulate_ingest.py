import httpx
import duckdb
import hashlib

DB_PATH = "alpha/newsletters.db"
OLLAMA_HOST = "http://localhost:11434"
MODEL = "nomic-embed-text:latest"

article = {
    "title": "Solaire dans le désert du Sahara",
    "sender": "solaire@news.dz",
    "source": "Sahara Solaire",
    "datetime": "2026-05-21 16:00:00",
    "url": "https://sahara-solaire.dz/article",
    "summary": "A new solar power plant has been initiated in the Sahara desert.",
    "original_language_summary": "Une nouvelle centrale solaire a été initiée dans le désert du Sahara.",
    "detected_language": "fr",
    "topics": "solaire, désert, Sahara",
    "themes": "infrastructure",
    "keywords": "Sahara, solaire, centrale",
    "entities": [
        ("LOC", "Sahara", "Sahara")
    ]
}

def get_embedding(text: str) -> list:
    url = f"{OLLAMA_HOST}/api/embed"
    body = {"model": MODEL, "input": text}
    resp = httpx.post(url, json=body, timeout=30.0)
    resp.raise_for_status()
    return resp.json()["embeddings"][0]

def main():
    print("Generating embeddings...")
    en_embed = get_embedding(article["summary"])
    multiling_embed = get_embedding(article["original_language_summary"])
    
    uid = hashlib.md5(article["title"].encode("utf-8")).hexdigest()
    
    print("Connecting to DuckDB...")
    con = duckdb.connect(DB_PATH)
    
    print(f"Inserting new newsletter: {article['title']} (uid: {uid})")
    con.execute(
        """
        INSERT INTO newsletters (
            uid, datetime, source, sender, title, url, summary, 
            original_language_summary, detected_language, truncated, 
            content_type, topics, themes, keywords, subscription_marketing, 
            english_embedding, multilingual_embedding
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            uid, article["datetime"], article["source"], article["sender"], article["title"], article["url"], 
            article["summary"], article["original_language_summary"], article["detected_language"],
            False, "Article", article["topics"], article["themes"], article["keywords"], False, 
            en_embed, multiling_embed
        )
    )
    
    for ent in article["entities"]:
        con.execute(
            "INSERT INTO entities (uid, entity_type, raw_name, canonical_name) VALUES (?, ?, ?, ?)",
            (uid, ent[0], ent[1], ent[2])
        )
        
    print("Simulation ingestion completed successfully.")
    con.close()

if __name__ == "__main__":
    main()
