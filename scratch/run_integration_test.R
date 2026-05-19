# Integration test script for Narrative Intelligence pipeline
# Configures local Ollama model (gemma4:e2b) and nomic-embed-text embeddings,
# runs extraction and database ingestion on mock multilingual articles.

library(jsonlite)
library(DBI)
library(duckdb)
library(digest)
library(dplyr)

# Set test environment variables
Sys.setenv(DUCKDB_PATH = "scratch/test_newsletters.db")
Sys.setenv(LLM_PROVIDER = "ollama")
Sys.setenv(LLM_MODEL = "gemma4:e2b")
Sys.setenv(EMBEDDING_PROVIDER = "ollama")
Sys.setenv(EMBEDDING_MODEL = "nomic-embed-text:latest")
Sys.setenv(OLLAMA_HOST = "http://localhost:11434")

# Source our pipeline modules
source("alpha/config.R")
source("alpha/db_manager.R")
source("alpha/model_adapter.R")
source("alpha/prompts.R")
source("alpha/entity_resolver.R")

# Ensure clean database state
if (file.exists("scratch/test_newsletters.db")) {
  message("Removing existing test database...")
  file.remove("scratch/test_newsletters.db")
}

# Create mock data items (representing English, French, and Portuguese articles)
mock_items <- list(
  list(
    uid = digest::digest("article_1", algo = "md5"),
    title = "TotalEnergies advances LNG exploration in Mozambique's Cabo Delgado",
    sender = "energy-insights@substack.com",
    source = "Energy Insights",
    datetime = "2026-05-18T10:00:00Z",
    body = "TotalEnergies is restarting its liquefied natural gas (LNG) project in Cabo Delgado, Mozambique, after security conditions improved. The project is expected to produce 13 million tons of LNG per year. Key organizations involved include TotalEnergies and Eni, with CEO Patrick Pouyanné visiting Maputo to coordinate with President Filipe Nyusi. The local communities in Palma and Mocímboa da Praia will benefit from development programs."
  ),
  list(
    uid = digest::digest("article_2", algo = "md5"),
    title = "Transition énergétique en Afrique de l'Ouest : La Cedeao soutient le solaire",
    sender = "contact@cedeao.int",
    source = "CEDEAO News",
    datetime = "2026-05-19T08:30:00Z",
    body = "La CEDEAO (Communauté Économique des États de l'Afrique de l'Ouest) a annoncé un nouveau fonds de 500 millions de dollars pour soutenir le développement de projets solaires hors réseau au Sénégal et au Mali. Le commissaire à l'énergie de la CEDEAO, Sékou Sangaré, a précisé que la Banque Ouest Africaine de Développement (BOAD) et la Banque mondiale codirigent l'initiative. Le but est de réduire la dépendance au charbon et de favoriser l'électrification rurale."
  ),
  list(
    uid = digest::digest("article_3", algo = "md5"),
    title = "Angola avança com novos projetos de energia solar em Benguela",
    sender = "info@jornaldeangola.ao",
    source = "Jornal de Angola",
    datetime = "2026-05-19T09:15:00Z",
    body = "O governo de Angola, representado pelo Ministério da Energia e Águas, assinou um acordo de financiamento com a empresa alemã GAUFF Engineering para construir três centrais solares fotovoltaicas na província de Benguela. O ministro João Baptista Borges destacou que a infraestrutura beneficiará mais de 200 mil famílias e ajudará o país a diversificar a sua matriz energética nacional, reduzindo o consumo de gasóleo."
  )
)

message("=== Starting Integration Test ===")
config <- get_config()
con <- get_db_connection(config$db_path)
init_db(con)

processed_count <- 0

for (item in mock_items) {
  message("\n------------------------------------------------")
  message("Processing article: ", item$title)
  message("Detected language parsing...")
  
  sys_prompt <- get_analysis_system_prompt()
  user_prompt <- construct_analysis_user_prompt(item$title, item$sender, item$body)
  
  message("Calling LLM adapter (Ollama: gemma4:e2b)...")
  llm_resp <- generate_completion(user_prompt, system_prompt = sys_prompt, json_mode = TRUE, config = config)
  
  # Clean potential markdown backticks
  llm_resp_clean <- gsub("^```json\\s*", "", llm_resp)
  llm_resp_clean <- gsub("\\s*```$", "", llm_resp_clean)
  
  message("Response: ", llm_resp_clean)
  parsed_analysis <- jsonlite::fromJSON(llm_resp_clean)
  
  # Embed summaries
  message("Generating embeddings...")
  en_embed <- generate_embeddings(parsed_analysis$summary_en, config, space = "english")[[1]]
  
  orig_summary_txt <- ifelse(!is.null(parsed_analysis$summary_orig) && parsed_analysis$summary_orig != "",
                             parsed_analysis$summary_orig,
                             parsed_analysis$summary_en)
  
  multiling_embed <- generate_embeddings(orig_summary_txt, config, space = "multilingual")[[1]]
  
  # Save to newsletters
  topics_str <- paste(parsed_analysis$topics, collapse = ", ")
  themes_str <- paste(parsed_analysis$themes, collapse = ", ")
  keywords_str <- paste(parsed_analysis$keywords, collapse = ", ")
  
  pub_author <- parsed_analysis$publisher_metadata$author
  pub_pub <- parsed_analysis$publisher_metadata$publisher
  pub_plat <- parsed_analysis$publisher_metadata$platform
  
  if (is.null(pub_author) || is.na(pub_author)) pub_author <- "Unknown"
  if (is.null(pub_pub) || is.na(pub_pub)) pub_pub <- item$source
  if (is.null(pub_plat) || is.na(pub_plat)) pub_plat <- item$source
  
  insert_sql <- "
      INSERT INTO newsletters (
          uid, datetime, source, sender, title, summary,
          original_language_summary, detected_language, truncated, content_type,
          topics, themes, keywords, subscription_marketing,
          english_embedding, multilingual_embedding
      ) VALUES (
          ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
      );
  "
  
  DBI::dbExecute(con, insert_sql, params = list(
    item$uid,
    as.POSIXct(item$datetime),
    pub_pub,
    item$sender,
    item$title,
    parsed_analysis$summary_en,
    parsed_analysis$summary_orig,
    parsed_analysis$detected_language,
    FALSE,
    pub_plat,
    topics_str,
    themes_str,
    keywords_str,
    as.logical(parsed_analysis$subscription_marketing),
    list(en_embed),
    list(multiling_embed)
  ))
  
  # Resolve entities after parent record is inserted
  if (!is.null(parsed_analysis$entities) && is.data.frame(parsed_analysis$entities) && nrow(parsed_analysis$entities) > 0) {
    message("Resolving entities:")
    print(parsed_analysis$entities)
    resolve_and_store_entities(item$uid, parsed_analysis$entities, con)
  }
  
  processed_count <- processed_count + 1
  message("Success!")
}

# Verify entries
message("\n=== Database Verification ===")
newsletters_count <- DBI::dbGetQuery(con, "SELECT COUNT(*) as count FROM newsletters;")$count
entities_count <- DBI::dbGetQuery(con, "SELECT COUNT(*) as count FROM entities;")$count
lexicon_count <- DBI::dbGetQuery(con, "SELECT COUNT(*) as count FROM entity_lexicon;")$count

message("Total articles in DB: ", newsletters_count)
message("Total entity occurrences in DB: ", entities_count)
message("Total unique canonical entities in Lexicon: ", lexicon_count)

message("\nTop canonical entities:")
print(DBI::dbGetQuery(con, "SELECT canonical_name, entity_type, COUNT(*) as occurrence_count FROM entities GROUP BY canonical_name, entity_type ORDER BY occurrence_count DESC;"))

close_db_connection(con)
message("\n=== Integration Test Successful ===")
