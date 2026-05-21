#' Connect to DuckDB Database
#'
#' Establishes a connection to the local DuckDB file and sets performance and memory constraints.
#'
#' @param db_path Path to the DuckDB file.
#' @return A DBI connection object.
#' @importFrom DBI dbConnect
#' @importFrom duckdb duckdb
#' @export
get_db_connection <- function(db_path) {
    # Ensure parent directory exists
    dir.create(dirname(db_path), recursive = TRUE, showWarnings = FALSE)
    
    # Establish connection
    con <- DBI::dbConnect(duckdb::duckdb(), db_path)
    
    # Enforce memory and thread safety constraints for resource-constrained VMs
    DBI::dbExecute(con, "SET max_memory = '512MB';")
    DBI::dbExecute(con, "SET threads = 1;")
    
    return(con)
}

#' Initialize Database Tables and Schemas
#'
#' Sets up the schema for newsletters, entities, and the entity lexicon lookup.
#'
#' @param con A DBI database connection.
#' @export
init_db <- function(con) {
    # 1. Create newsletters table
    DBI::dbExecute(con, "
        CREATE TABLE IF NOT EXISTS newsletters (
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
    ")
    
    # Schema migration check: Ensure 'url' column exists in existing databases
    cols <- DBI::dbGetQuery(con, "PRAGMA table_info('newsletters');")
    if (!("url" %in% cols$name)) {
        message("Migration: Adding 'url' column to existing newsletters table.")
        DBI::dbExecute(con, "ALTER TABLE newsletters ADD COLUMN url VARCHAR;")
    }
    
    # 2. Create entity ID sequence and entities table
    DBI::dbExecute(con, "CREATE SEQUENCE IF NOT EXISTS entity_id_seq;")
    DBI::dbExecute(con, "
        CREATE TABLE IF NOT EXISTS entities (
            entity_id INTEGER DEFAULT nextval('entity_id_seq') PRIMARY KEY,
            uid VARCHAR,
            entity_type VARCHAR,
            raw_name VARCHAR,
            canonical_name VARCHAR,
            FOREIGN KEY (uid) REFERENCES newsletters(uid)
        );
    ")
    
    # 3. Create entity lexicon table for deduplication
    DBI::dbExecute(con, "
        CREATE TABLE IF NOT EXISTS entity_lexicon (
            raw_name VARCHAR PRIMARY KEY,
            canonical_name VARCHAR,
            entity_type VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ")
    
    message("DuckDB tables initialized successfully.")
}

#' Close Database Connection
#'
#' Safely closes the database connection and releases memory.
#'
#' @param con A DBI database connection.
#' @export
close_db_connection <- function(con) {
    if (!is.null(con)) {
        DBI::dbDisconnect(con, shutdown = TRUE)
    }
}
