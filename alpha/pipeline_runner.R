# Narrative Intelligence Ingestion Pipeline Orchestrator
#
# Coordinates modular ingestion sources (Gmail, RSS, Telegram, Substack),
# runs LLM-based translation and entity extraction, computes dual-space vector
# embeddings, runs entity lexicon deduplication, and commits to local DuckDB.

# Load modules
source("alpha/config.R")
source("alpha/db_manager.R")
source("alpha/model_adapter.R")
source("alpha/prompts.R")
source("alpha/email_ingester.R")
source("alpha/rss_ingester.R")
source("alpha/telegram_ingester.R")
source("alpha/subscription_ingester.R")
source("alpha/fediverse_ingester.R")
source("alpha/entity_resolver.R")

library(jsonlite)
library(DBI)
library(duckdb)
library(digest)
library(dplyr)

#' Clean and format a R vector to DuckDB FLOAT[] list representation
#'
#' @param vec Numeric vector of embeddings.
#' @return SQL string format e.g. '[0.1, 0.2, ...]'
format_vector_for_duckdb <- function(vec) {
    if (is.null(vec) || length(vec) == 0 || any(is.na(vec))) {
        return(NULL)
    }
    # Create literal array: array[0.1, 0.2, ...]
    paste0("ARRAY[", paste(vec, collapse = ", "), "]")
}

#' Run Ingestion and Process New Articles
#'
#' @param rss_feeds Named list of RSS URLs: list(feed_name = "url")
#' @param telegram_channels Character vector of telegram channel names
#' @param subscription_feeds Named list of substack/ghost feeds
#' @param fediverse_handles Character vector of Fediverse/Mastodon handles
#' @export
run_pipeline <- function(rss_feeds = list(), telegram_channels = c(), subscription_feeds = list(), fediverse_handles = c()) {
    message("--- Initializing Pipeline Run ---")
    config <- get_config()
    
    # 1. Establish DB Connection
    con <- get_db_connection(config$db_path)
    on.exit(close_db_connection(con))
    init_db(con)
    
    # 2. Ingest raw items from sources
    raw_items <- list()
    
    # A. Fetch Gmail newsletters if credentials configured
    if (config$gmail_username != "" && config$gmail_app_password != "") {
        message("\n[Pipeline] Ingesting Gmail inbox...")
        gmail_recs <- tryCatch({
            fetch_new_emails(config)
        }, error = function(e) {
            message("Gmail ingestion failed: ", e$message)
            return(list())
        })
        if (length(gmail_recs) > 0) {
            gmail_recs <- lapply(gmail_recs, function(x) { x$platform <- "email"; x })
            raw_items <- c(raw_items, gmail_recs)
        }
    }
    
    # B. Fetch RSS Feeds
    if (length(rss_feeds) > 0) {
        message("\n[Pipeline] Ingesting RSS feeds...")
        for (name in names(rss_feeds)) {
            rss_recs <- tryCatch({
                fetch_rss_feed(rss_feeds[[name]], feed_name = name)
            }, error = function(e) {
                message("RSS feed failed (", name, "): ", e$message)
                return(list())
            })
            if (length(rss_recs) > 0) {
                rss_recs <- lapply(rss_recs, function(x) { x$platform <- "rss"; x })
                raw_items <- c(raw_items, rss_recs)
            }
        }
    }
    
    # C. Fetch Telegram channels
    if (length(telegram_channels) > 0) {
        message("\n[Pipeline] Ingesting Telegram channels...")
        for (chan in telegram_channels) {
            tg_recs <- tryCatch({
                fetch_telegram_channel(chan)
            }, error = function(e) {
                message("Telegram channel failed (", chan, "): ", e$message)
                return(list())
            })
            if (length(tg_recs) > 0) {
                tg_recs <- lapply(tg_recs, function(x) { x$platform <- "telegram"; x })
                raw_items <- c(raw_items, tg_recs)
            }
        }
    }
    
    # D. Fetch Subscription feeds (Substack/Ghost)
    if (length(subscription_feeds) > 0) {
        message("\n[Pipeline] Ingesting Substack/Ghost subscription feeds...")
        for (name in names(subscription_feeds)) {
            sub_recs <- tryCatch({
                fetch_subscription_feed(subscription_feeds[[name]], publisher_name = name)
            }, error = function(e) {
                message("Subscription feed failed (", name, "): ", e$message)
                return(list())
            })
            if (length(sub_recs) > 0) {
                sub_recs <- lapply(sub_recs, function(x) { x$platform <- "subscription"; x })
                raw_items <- c(raw_items, sub_recs)
            }
        }
    }
    
    # E. Fetch Fediverse accounts
    if (length(fediverse_handles) > 0) {
        message("\n[Pipeline] Ingesting Fediverse accounts...")
        for (handle in fediverse_handles) {
            fedi_recs <- tryCatch({
                fetch_fediverse_posts(handle)
            }, error = function(e) {
                message("Fediverse ingestion failed for handle (", handle, "): ", e$message)
                return(list())
            })
            if (length(fedi_recs) > 0) {
                fedi_recs <- lapply(fedi_recs, function(x) { x$platform <- "fediverse"; x })
                raw_items <- c(raw_items, fedi_recs)
            }
        }
    }
    
    if (length(raw_items) == 0) {
        message("\nNo new raw items fetched from any sources. Pipeline execution complete.")
        return(invisible(NULL))
    }
    
    message("\nFetched total ", length(raw_items), " raw items. Commencing duplicate check...")
    
    # 3. Check for duplicates against existing DB records
    processed_count <- 0
    
    for (item in raw_items) {
        uid <- item$uid
        
        # Check if record already exists in newsletters table
        exists_query <- "SELECT 1 FROM newsletters WHERE uid = ?;"
        exists_res <- DBI::dbGetQuery(con, exists_query, params = list(uid))
        
        if (nrow(exists_res) > 0) {
            # Skip duplicate
            next
        }
        
        message("\n--- Processing New Record ---")
        message("Title: ", item$title)
        message("Source: ", item$source)
        
        # 4. Truncate text if needed (cap at 12,000 words to fit model contexts)
        content_words <- unlist(strsplit(item$body, "\\s+"))
        truncated_flag <- FALSE
        content_to_llm <- item$body
        if (length(content_words) > 12000) {
            content_to_llm <- paste(content_words[1:12000], collapse = " ")
            truncated_flag <- TRUE
            message("Warning: Article content truncated to 12,000 words.")
        }
        
        # 5. Extract metadata, translation summaries, and entities via LLM
        sys_prompt <- get_analysis_system_prompt()
        user_prompt <- construct_analysis_user_prompt(item$title, item$sender, content_to_llm)
        
        llm_resp <- tryCatch({
            generate_completion(user_prompt, system_prompt = sys_prompt, json_mode = TRUE, config = config)
        }, error = function(e) {
            message("LLM Extraction failed for article: ", item$title, ". Error: ", e$message)
            return(NULL)
        })
        
        if (is.null(llm_resp)) next
        
        # Clean response string in case LLM added markdown backticks
        llm_resp_clean <- gsub("^```json\\s*", "", llm_resp)
        llm_resp_clean <- gsub("\\s*```$", "", llm_resp_clean)
        
        parsed_analysis <- tryCatch({
            jsonlite::fromJSON(llm_resp_clean)
        }, error = function(e) {
            message("JSON Parsing error of LLM response. Skipping item. Error: ", e$message)
            return(NULL)
        })
        
        if (is.null(parsed_analysis)) next
        
        # Enforce summary_orig = summary_en programmatically when detected_language == "en"
        if (!is.null(parsed_analysis$detected_language) && parsed_analysis$detected_language == "en") {
            parsed_analysis$summary_orig <- parsed_analysis$summary_en
        }
        
        # 6. Generate Vector Embeddings
        topics_str <- paste(parsed_analysis$topics, collapse = ", ")
        themes_str <- paste(parsed_analysis$themes, collapse = ", ")
        
        # Combine summary with topics and themes to ensure they are captured in the vector space
        embedding_text_en <- paste0(
            parsed_analysis$summary_en, 
            "\nTopics: ", topics_str, 
            "\nThemes: ", themes_str
        )
        
        # English Vector (embeds English summary + topics + themes)
        message("Generating English summary embedding...")
        en_embed <- tryCatch({
            generate_embeddings(embedding_text_en, config, space = "english")[[1]]
        }, error = function(e) {
            message("English embedding generation failed: ", e$message)
            return(NULL)
        })
        
        # Multilingual Vector (embeds original language summary + topics + themes)
        message("Generating Multilingual summary embedding...")
        orig_summary_txt <- ifelse(!is.null(parsed_analysis$summary_orig) && parsed_analysis$summary_orig != "",
                                   parsed_analysis$summary_orig,
                                   parsed_analysis$summary_en)
        embedding_text_orig <- paste0(
            orig_summary_txt,
            "\nTopics: ", topics_str,
            "\nThemes: ", themes_str
        )
        multiling_embed <- tryCatch({
            generate_embeddings(embedding_text_orig, config, space = "multilingual")[[1]]
        }, error = function(e) {
            message("Multilingual embedding generation failed: ", e$message)
            return(NULL)
        })
        
        # 7. Deduplicate and Save Entities
        # Parse publisher metadata
        pub_author <- parsed_analysis$publisher_metadata$author
        pub_pub <- parsed_analysis$publisher_metadata$publisher
        
        # Enforce platform tagging based on actual ingestion tool/source type
        pub_plat <- if (!is.null(item$platform)) item$platform else parsed_analysis$publisher_metadata$platform
        
        # Fallbacks
        if (is.null(pub_author) || is.na(pub_author)) pub_author <- "Unknown"
        if (is.null(pub_pub) || is.na(pub_pub)) pub_pub <- item$source
        if (is.null(pub_plat) || is.na(pub_plat)) pub_plat <- item$source
        
        # 8. Save Record to newsletters table
        # We need to construct the lists as comma separated strings
        topics_str <- paste(parsed_analysis$topics, collapse = ", ")
        themes_str <- paste(parsed_analysis$themes, collapse = ", ")
        keywords_str <- paste(parsed_analysis$keywords, collapse = ", ")
        
        # Enforce timestamp parsing
        parsed_dt <- tryCatch({
            as.POSIXct(item$datetime)
        }, error = function(e) Sys.time())
        if (is.na(parsed_dt)) parsed_dt <- Sys.time()
        
        # Set parameters
        insert_sql <- "
            INSERT INTO newsletters (
                uid, datetime, source, sender, title, url, summary,
                original_language_summary, detected_language, truncated, content_type,
                topics, themes, keywords, subscription_marketing,
                english_embedding, multilingual_embedding
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            );
        "
        
        # Execute query using DBI parameter bindings
        # Note: DuckDB R driver supports native list types, but passing numeric vectors directly works
        # when formatted or bound as lists. Let's pass them as R numeric vectors, which duckdb DBI maps.
        DBI::dbExecute(con, insert_sql, params = list(
            uid,
            parsed_dt,
            pub_pub,
            item$sender,
            item$title,
            item$url,
            parsed_analysis$summary_en,
            parsed_analysis$summary_orig,
            parsed_analysis$detected_language,
            truncated_flag,
            pub_plat,
            topics_str,
            themes_str,
            keywords_str,
            as.logical(parsed_analysis$subscription_marketing),
            list(en_embed),
            list(multiling_embed)
        ))
        
        # Resolve entities database-side after parent record exists
        if (!is.null(parsed_analysis$entities) && is.data.frame(parsed_analysis$entities) && nrow(parsed_analysis$entities) > 0) {
            message("Resolving and storing ", nrow(parsed_analysis$entities), " entities...")
            tryCatch({
                resolve_and_store_entities(uid, parsed_analysis$entities, con)
            }, error = function(e) {
                message("Entity resolving failed: ", e$message)
            })
        }
        
        processed_count <- processed_count + 1
        message("Successfully saved record to DuckDB: ", item$title)
    }
    
    message("\n--- Pipeline Run Complete. Processed ", processed_count, " new articles ---")
    
    # 9. Sync copy of DB to external Cloud Storage bucket if configured
    if (config$gcs_bucket_name != "") {
        message("\n[Pipeline] Syncing database to GCS: ", config$gcs_bucket_name)
        # Note: Handled by system gsutil/aws sync command or Python sync subagent
        # We'll print instructions for the FastAPI startup replication.
    }
}
