#' Load Phase 2 Pipeline Configuration
#'
#' Reads environment variables and returns a structured list of configuration options.
#'
#' @return A list containing configuration values.
#' @export
get_config <- function() {
    # Ingestion configuration
    gmail_username <- Sys.getenv("GMAIL_USERNAME", unset = "")
    gmail_app_password <- Sys.getenv("GMAIL_APP_PASSWORD", unset = "")
    
    # DB configuration
    db_path <- Sys.getenv("DUCKDB_PATH", unset = "alpha/newsletters.db")
    
    # Model agnosticism configuration
    llm_provider <- Sys.getenv("LLM_PROVIDER", unset = "openrouter")
    llm_model <- Sys.getenv("LLM_MODEL", unset = "deepseek/deepseek-chat")
    
    embedding_provider <- Sys.getenv("EMBEDDING_PROVIDER", unset = "openrouter")
    embedding_model <- Sys.getenv("EMBEDDING_MODEL", unset = "nomic-embed-text")
    
    # Provider keys & hosts
    openrouter_api_key <- Sys.getenv("OPENROUTER_API_KEY", unset = "")
    ollama_host <- Sys.getenv("OLLAMA_HOST", unset = "http://localhost:11434")
    openai_api_key <- Sys.getenv("OPENAI_API_KEY", unset = "")
    gemini_api_key <- Sys.getenv("GEMINI_API_KEY", unset = "")
    
    # Sync configuration
    gcs_bucket_name <- Sys.getenv("GCS_BUCKET_NAME", unset = "")
    
    # State tracking configuration
    last_email_id_file <- Sys.getenv("LAST_EMAIL_ID_FILE", unset = "alpha/last_email_id.txt")
    
    # Forensic Logging configuration
    forensic_log_path <- Sys.getenv("FORENSIC_LOG_PATH", unset = "FORENSIC_LOG")
    
    config <- list(
        gmail_username = gmail_username,
        gmail_app_password = gmail_app_password,
        db_path = db_path,
        llm_provider = llm_provider,
        llm_model = llm_model,
        embedding_provider = embedding_provider,
        embedding_model = embedding_model,
        openrouter_api_key = openrouter_api_key,
        ollama_host = ollama_host,
        openai_api_key = openai_api_key,
        gemini_api_key = gemini_api_key,
        gcs_bucket_name = gcs_bucket_name,
        last_email_id_file = last_email_id_file,
        forensic_log_path = forensic_log_path
    )
    
    return(config)
}
