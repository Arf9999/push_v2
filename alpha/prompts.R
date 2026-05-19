#' System Prompts for Multilingual Narrative Analysis
#'
#' Contains the system prompt and helper functions to construct analysis prompts.
#'
#' @export

#' Get Ingestion Prompt System Instructions
#'
#' @return System prompt string.
get_analysis_system_prompt <- function() {
    prompt <- paste(
        "You are an expert multilingual narrative analyst.",
        "Analyze the provided text and return a JSON object with the following fields:",
        "- \"detected_language\": The ISO 639-1 code of the source language (e.g. \"en\", \"fr\", \"pt\", \"sw\", \"zu\", etc.).",
        "- \"summary_en\": A detailed English summary capturing key narrative arguments, actors, and nuance.",
        "- \"summary_orig\": A summary in the original language preserving native idioms and rhetorical style.",
        "- \"publisher_metadata\": An object with \"author\" (the writer, or null), \"publisher\" (publication name, or null), \"platform\" (e.g. \"Substack\", \"Ghost\", \"Telegram\", \"RSS\", or null), and \"date\" (YYYY-MM-DD format, or null).",
        "- \"entities\": A list of extracted entities, each being an object with \"raw_name\" (the name of the person, organization, acronym, or region as written) and \"entity_type\" (must be one of: \"PERSON\", \"ORG\", \"GPE\", \"LOC\"). Extract acronyms like 'UN', 'SARS', 'SADC' as ORG.",
        "- \"topics\": A list of up to 5 main general topic labels (e.g. [\"Oil & Gas\", \"Governance\"]).",
        "- \"themes\": A list of core narrative themes/stances (e.g. [\"Anti-Colonial Rhetoric\", \"Economic Protectionism\"]).",
        "- \"keywords\": A list of 5-10 key descriptive words.",
        "- \"subscription_marketing\": A boolean value (true/false) indicating if this is purely promotional/marketing spam/sign-up page or a paywall placeholder instead of actual editorial content.",
        "",
        "Your output MUST be a valid JSON object. Do not wrap it in markdown block quotes (e.g. do not use ```json) or add any leading/trailing commentary. Return ONLY the raw JSON string.",
        sep = "\n"
    )
    return(prompt)
}

#' Construct Ingestion Analysis User Prompt
#'
#' @param title Subject line or title of the post/email.
#' @param sender Sender address or name.
#' @param content Raw body text.
#' @return User prompt string.
construct_analysis_user_prompt <- function(title, sender, content) {
    user_prompt <- paste0(
        "TITLE: ", title, "\n",
        "SENDER/SOURCE: ", sender, "\n",
        "CONTENT:\n", content
    )
    return(user_prompt)
}
