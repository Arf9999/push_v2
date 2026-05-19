# Diagnostic Test: Database Initialization and Configuration
# Resides in scratch/ to avoid production pipeline pollution.

message("=== Testing Pipeline Scaffolding ===")

# Source local files
source("alpha/config.R")
source("alpha/db_manager.R")

# 1. Parse Config
message("\n[Test 1] Parsing configuration settings...")
config <- get_config()
str(config)

# 2. Establish DB Connection and Init Tables
message("\n[Test 2] Connecting to local DuckDB and creating schemas...")
con <- NULL
tryCatch({
    con <- get_db_connection(config$db_path)
    init_db(con)
    
    # Check max memory and threads setting
    mem_res <- DBI::dbGetQuery(con, "PRAGMA max_memory;")
    thread_res <- DBI::dbGetQuery(con, "PRAGMA threads;")
    
    message("Database Memory Limit: ", mem_res$max_memory)
    message("Database Active Threads: ", thread_res$threads)
    
    # Verify tables exist
    tables <- DBI::dbListTables(con)
    message("Database Tables found: ", paste(tables, collapse = ", "))
    
    if (all(c("newsletters", "entities", "entity_lexicon") %in% tables)) {
        message("SUCCESS: All tables created successfully.")
    } else {
        message("FAILURE: Missing expected tables.")
    }
}, error = function(e) {
    message("Error during database test: ", e$message)
}, finally = {
    if (!is.null(con)) {
        close_db_connection(con)
        message("Database connection shut down safely.")
    }
})

message("\n=== Diagnostic Test Complete ===")
