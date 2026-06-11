# scratch/reembed_corpus.R
# Maintenance utility script to re-embed all articles in the DuckDB database
# using the currently configured embedding provider and model.

source("alpha/config.R")
source("alpha/db_manager.R")
source("alpha/model_adapter.R")

library(DBI)
library(duckdb)

reembed_database <- function() {
    config <- get_config()
    message("=== Narrative Intelligence Database Re-embedding ===")
    message("Target Database:    ", config$db_path)
    message("Embedding Provider: ", config$embedding_provider)
    message("Embedding Model:    ", config$embedding_model)
    
    # 1. Establish DB Connection
    if (!file.exists(config$db_path)) {
        stop("Database file not found at: ", config$db_path)
    }
    
    con <- get_db_connection(config$db_path)
    on.exit(close_db_connection(con))
    
    # 2. Query all existing records
    message("\nFetching records from newsletters table...")
    records <- DBI::dbGetQuery(con, "SELECT uid, summary, original_language_summary, topics, themes FROM newsletters;")
    
    total_records <- nrow(records)
    if (total_records == 0) {
        message("No records found in the database. Nothing to re-embed.")
        return(invisible(NULL))
    }
    
    message("Found ", total_records, " articles to process.")
    
    # 3. Process and update each record
    success_count <- 0
    for (i in 1:total_records) {
        uid <- records$uid[i]
        summary_en <- records$summary[i]
        summary_orig <- records$original_language_summary[i]
        topics_str <- records$topics[i]
        themes_str <- records$themes[i]
        
        # Fallback if original language summary is empty
        if (is.null(summary_orig) || is.na(summary_orig) || summary_orig == "") {
            summary_orig <- summary_en
        }
        
        # Format strings (handle missing topics/themes gracefully)
        if (is.null(topics_str) || is.na(topics_str)) topics_str <- ""
        if (is.null(themes_str) || is.na(themes_str)) themes_str <- ""
        
        embedding_text_en <- paste0(
            summary_en,
            "\nTopics: ", topics_str,
            "\nThemes: ", themes_str
        )
        
        embedding_text_orig <- paste0(
            summary_orig,
            "\nTopics: ", topics_str,
            "\nThemes: ", themes_str
        )
        
        message(sprintf("[%d/%d] Processing article UID: %s", i, total_records, uid))
        
        # Generate new embeddings
        en_embed <- tryCatch({
            generate_embeddings(embedding_text_en, config, space = "english")[[1]]
        }, error = function(e) {
            message("  [Error] English embedding failed: ", e$message)
            NULL
        })
        
        multiling_embed <- tryCatch({
            generate_embeddings(embedding_text_orig, config, space = "multilingual")[[1]]
        }, error = function(e) {
            message("  [Error] Multilingual embedding failed: ", e$message)
            NULL
        })
        
        if (is.null(en_embed) || is.null(multiling_embed)) {
            message("  [Warning] Skipping update due to embedding failures.")
            next
        }
        
        # Update row in DuckDB
        update_sql <- "
            UPDATE newsletters 
            SET english_embedding = ?, multilingual_embedding = ?
            WHERE uid = ?;
        "
        
        tryCatch({
            DBI::dbExecute(con, update_sql, params = list(
                list(en_embed),
                list(multiling_embed),
                uid
            ))
            success_count <- success_count + 1
        }, error = function(e) {
            message("  [Error] Database update failed: ", e$message)
        })
    }
    
    message("\n=== Re-embedding complete ===")
    message(sprintf("Successfully updated %d out of %d articles.", success_count, total_records))
}

# Run the function
reembed_database()
