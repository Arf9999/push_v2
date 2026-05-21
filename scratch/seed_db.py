import os
import httpx
import duckdb
import hashlib
from datetime import datetime

DB_PATH = "alpha/newsletters.db"
OLLAMA_HOST = "http://localhost:11434"
MODEL = "nomic-embed-text:latest"

articles = [
    {
        "title": "Eskom and South Africa's Energy Grid Resilience Plan",
        "sender": "energy-insights@substack.com",
        "source": "Energy Insights",
        "datetime": "2026-05-20 10:00:00",
        "url": "https://energy-insights.substack.com/p/eskom-grid-resilience",
        "summary": "Eskom Holdings is accelerating grid updates in South Africa to ensure long-term energy security.",
        "original_language_summary": "Eskom Holdings is accelerating grid updates in South Africa to ensure long-term energy security.",
        "detected_language": "en",
        "topics": "energy, electricity, grid",
        "themes": "infrastructure, governance",
        "keywords": "Eskom, South Africa, grid, solar",
        "entities": [
            ("ORG", "Eskom Holdings", "Eskom"),
            ("LOC", "South Africa", "South Africa")
        ]
    },
    {
        "title": "Transition énergétique en Afrique de l'Ouest : La Cedeao soutient le solaire",
        "sender": "contact@cedeao.int",
        "source": "CEDEAO News",
        "datetime": "2026-05-20 12:00:00",
        "url": "https://cedeao.int/news/transition-energetique-afrique-ouest",
        "summary": "The ECOWAS Commission announced a new fund to support off-grid solar energy projects in Senegal and Mali.",
        "original_language_summary": "La CEDEAO a annoncé un nouveau fonds pour soutenir le développement de projets solaires au Sénégal et au Mali.",
        "detected_language": "fr",
        "topics": "solaire, énergie, ouest-africaine",
        "themes": "développement, transition",
        "keywords": "CEDEAO, Sénégal, Mali, solaire",
        "entities": [
            ("ORG", "La CEDEAO", "ECOWAS"),
            ("LOC", "Sénégal", "Senegal"),
            ("LOC", "Mali", "Mali")
        ]
    },
    {
        "title": "New Solar Energy Breakthrough in Angola Benguela",
        "sender": "info@jornaldeangola.ao",
        "source": "Jornal de Angola",
        "datetime": "2026-05-21 15:00:00",
        "url": "https://jornaldeangola.ao/news/angola-avanca-novos-projetos-energia-solar-benguela",
        "summary": "Angola signed a financing agreement with GAUFF Engineering to construct three solar PV power stations.",
        "original_language_summary": "O governo de Angola assinou um acordo de financiamento com a empresa alemã GAUFF Engineering para construir três centrais solares.",
        "detected_language": "pt",
        "topics": "energia solar, eletricidade, Benguela",
        "themes": "infraestrutura, acordos",
        "keywords": "Angola, GAUFF, Benguela, solar",
        "entities": [
            ("LOC", "Angola", "Angola"),
            ("ORG", "GAUFF Engineering", "GAUFF Engineering"),
            ("LOC", "Benguela", "Benguela")
        ]
    }
]

def get_embedding(text: str) -> list:
    url = f"{OLLAMA_HOST}/api/embed"
    body = {"model": MODEL, "input": text}
    resp = httpx.post(url, json=body, timeout=30.0)
    resp.raise_for_status()
    return resp.json()["embeddings"][0]

def main():
    print("Connecting to DuckDB...")
    con = duckdb.connect(DB_PATH)
    
    print("Cleaning existing articles...")
    con.execute("DELETE FROM entities;")
    con.execute("DELETE FROM newsletters;")
    
    for art in articles:
        print(f"Generating embeddings for: {art['title']}")
        en_embed = get_embedding(art["summary"])
        multiling_embed = get_embedding(art["original_language_summary"])
        
        uid = hashlib.md5(art["title"].encode("utf-8")).hexdigest()
        
        print(f"Inserting newsletter: {art['title']} (uid: {uid})")
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
                uid, art["datetime"], art["source"], art["sender"], art["title"], art["url"], 
                art["summary"], art.get("original_language_summary"), art["detected_language"],
                False, "Article", art["topics"], art["themes"], art["keywords"], False, 
                en_embed, multiling_embed
            )
        )
        
        for ent in art["entities"]:
            con.execute(
                "INSERT INTO entities (uid, entity_type, raw_name, canonical_name) VALUES (?, ?, ?, ?)",
                (uid, ent[0], ent[1], ent[2])
            )
            
    print("Database seeding completed successfully.")
    con.close()

if __name__ == "__main__":
    main()
