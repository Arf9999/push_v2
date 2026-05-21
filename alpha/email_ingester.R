#' Email Ingestion Module
#'
#' Rewritten ingestion script for secure IMAP Gmail retrieval and parsing.
#' Decoupled from orchestrator, with custom text extraction and cursor tracking.
#'
#' @importFrom mRpostman configure_imap
#' @importFrom stringr str_match str_c str_detect str_split str_trim str_squish str_replace_all
#' @importFrom XML htmlParse xpathSApply xmlValue
#' @importFrom mime quoted_printable_decode
#' @importFrom purrr map_chr map
#' @importFrom tibble tibble
#' @importFrom dplyr %>%
#' @export

#' Connect to Gmail IMAP Server
#'
#' @param username Gmail username (email address).
#' @param password Gmail App Password.
#' @return An IMAP connection object.
connect_to_gmail <- function(username, password) {
    if (username == "" || password == "") {
        stop("Gmail username or App Password is not configured.")
    }
    
    con <- mRpostman::configure_imap(
        url = "imaps://imap.gmail.com",
        username = username,
        password = password,
        use_ssl = TRUE,
        verbose = FALSE,
        timeout_ms = 30000
    )
    
    return(con)
}

#' Remove Junk Email Headers
#'
#' @param text Raw text lines.
#' @return Cleaned string.
remove_junk_lines <- function(text) {
    if (is.na(text) || text == "") return("")
    lines <- stringr::str_split(text, "\n")[[1]]
    junk_patterns <- c("(?i)^\\s*content-type:", "(?i)^\\s*content-transfer-encoding:")
    combined_pattern <- paste0("(", paste(junk_patterns, collapse = ")|("), ")")
    keep_lines <- !grepl(combined_pattern, lines, perl = TRUE)
    cleaned <- paste(lines[keep_lines], collapse = "\n")
    cleaned <- stringr::str_replace_all(cleaned, "\n{2,}", "\n")
    stringr::str_squish(cleaned)
}

#' Extract Body Content from Email
#'
#' Handles multipart boundary slicing and HTML-to-text conversion.
#'
#' @param email_text Raw MIME email string.
#' @return Extracted plain body text.
extract_email_body <- function(email_text) {
    boundary <- stringr::str_match(email_text, 'boundary="([^"]+)"')[, 2]
    body_part <- NA_character_
    
    if (!is.na(boundary)) {
        pat <- stringr::str_c("(?s)--", boundary, "\\s*Content-Type:\\s*text/plain[^\\r\\n]*\\r?\\n\\r?\\n", "(.*?)(?=\\r?\\n--", boundary, ")")
        body_part <- stringr::str_match(email_text, pat)[, 2]
    }
    
    if (is.na(body_part) || stringr::str_trim(body_part) == "") {
        parts <- stringr::str_split(email_text, "\r?\n\r?\n", n = 2)[[1]]
        candidate <- if (length(parts) > 1) parts[2] else ""
        if (stringr::str_detect(candidate, "<html")) {
            body_part <- tryCatch({
                parsed_html <- XML::htmlParse(candidate, asText = TRUE)
                XML::xpathSApply(parsed_html, "//text()[not(ancestor::script)][not(ancestor::style)]", XML::xmlValue) %>%
                    paste(collapse = " ")
            }, error = function(e) candidate)
        } else {
            body_part <- candidate
        }
    }
    
    body_part <- tryCatch(mime::quoted_printable_decode(body_part), error = function(e) body_part)
    cleaned <- stringr::str_squish(body_part)
    cleaned <- remove_junk_lines(cleaned)
    return(cleaned)
}

#' Process Raw Email Into Structured Record
#'
#' @param email_text Raw MIME content.
#' @param uid The IMAP unique identifier.
#' @return A list containing parsed metadata fields and body text.
process_email_record <- function(email_text, uid) {
    from_field <- stringr::str_match(email_text, stringr::regex("^From:\\s*(.*)", multiline = TRUE))[, 2]
    subj_field <- stringr::str_match(email_text, stringr::regex("^Subject:\\s*(.*)", multiline = TRUE))[, 2]
    date_field <- stringr::str_match(email_text, stringr::regex("^Date:\\s*(.*)", multiline = TRUE))[, 2]
    
    from_field <- ifelse(is.na(from_field), "Unknown Sender", stringr::str_trim(from_field))
    subj_field <- ifelse(is.na(subj_field), "No Subject", stringr::str_trim(subj_field))
    date_field <- ifelse(is.na(date_field), "Unknown Date", stringr::str_trim(date_field))
    
    body <- extract_email_body(email_text)
    
    # Parse sender email address from "Name <email@address.com>" formats
    sender_email <- from_field
    email_regex <- "<([^>]+)>"
    if (stringr::str_detect(from_field, email_regex)) {
        sender_email <- stringr::str_match(from_field, email_regex)[, 2]
    }
    
    list(
        uid = uid,
        datetime = date_field,
        source = "Email Intake",
        sender = sender_email,
        title = subj_field,
        url = NA_character_,
        body = body
    )
}

#' Fetch and Parse Unread Emails
#'
#' Searches the INBOX for UIDs higher than the last processed UID, fetches their content,
#' parses them, and saves the new high watermark.
#'
#' @param config Config list.
#' @return A list of parsed email records.
#' @export
fetch_new_emails <- function(config) {
    con <- connect_to_gmail(config$gmail_username, config$gmail_app_password)
    on.exit(try(con$close(), silent = TRUE))
    
    con$select_folder("INBOX")
    
    # Read last email ID cursor
    last_uid <- NULL
    if (file.exists(config$last_email_id_file)) {
        last_uid_raw <- readLines(config$last_email_id_file, warn = FALSE)
        if (length(last_uid_raw) > 0 && last_uid_raw != "") {
            last_uid <- as.numeric(last_uid_raw)
        }
    }
    
    # Formulate IMAP search query
    search_query <- if (!is.null(last_uid)) paste0("UID ", last_uid + 1, ":*") else "ALL"
    message("Fetching emails matching query: ", search_query)
    
    emails_uids <- con$search(request = search_query)
    
    if (length(emails_uids) == 0) {
        message("No new emails found.")
        return(list())
    }
    
    # Fetch body text
    message("Fetching ", length(emails_uids), " email body contents...")
    email_data <- con$fetch_body(msg_id = emails_uids)
    
    records <- list()
    for (i in seq_along(email_data)) {
        raw_msg <- email_data[[i]]
        uid_str <- names(email_data)[i]
        
        # Parse email
        rec <- process_email_record(raw_msg, uid_str)
        records[[length(records) + 1]] <- rec
    }
    
    # Update last processed UID cursor
    max_uid <- max(as.numeric(emails_uids))
    writeLines(as.character(max_uid), config$last_email_id_file)
    message("Email ingestion complete. Cursor updated to UID ", max_uid)
    
    return(records)
}
