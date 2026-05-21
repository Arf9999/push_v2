# Diagnostic Test Script for Fediverse Ingesting
#
# Validates the parsing, HTML cleaning, and fetching capabilities
# of alpha/fediverse_ingester.R.

library(jsonlite)
library(digest)
library(dplyr)

# Set test environment
Sys.setenv(DUCKDB_PATH = "scratch/test_newsletters.db")

# Source files
source("alpha/config.R")
source("alpha/fediverse_ingester.R")

message("=== Starting Fediverse Diagnostic Tests ===")

# 1. Test handle parsing
message("\n--- Testing handle parsing ---")
test_handles <- c("@Gargron@mastodon.social", "Gargron@mastodon.social", "@index@www.newsroom.co.za")
for (h in test_handles) {
  parsed <- parse_fediverse_handle(h)
  message(sprintf("Input: %s => Username: %s, Domain: %s", h, parsed$username, parsed$domain))
}

# Test invalid handle
tryCatch({
  parse_fediverse_handle("invalid_handle")
}, error = function(e) {
  message("Caught expected error for invalid handle: ", e$message)
})

# 2. Test HTML Cleaning
message("\n--- Testing HTML cleaning ---")
dirty_html <- "<p>Hello &amp; welcome to the <a href='https://mastodon.social'>Fediverse</a>!&nbsp;This is a &quot;test&quot; &lt;post&gt;.</p>"
cleaned <- clean_fediverse_html(dirty_html)
message("Original: ", dirty_html)
message("Cleaned : ", cleaned)


# 2b. Test Article Link Filtering
message("\n--- Testing Article Link Filtering ---")
test_urls <- c(
  "https://www.newsroom.co.za/@index",
  "https://www.newsroom.co.za/@index/108392019382019",
  "https://www.newsroom.co.za/tags/energy",
  "https://www.newsroom.co.za/reports/energy-grid",
  "https://example.com/some/article",
  "https://mastodon.social/media/12345"
)
for (url in test_urls) {
  is_art <- is_actual_article_link(url)
  message(sprintf("URL: %s => Is Article Link: %s", url, is_art))
}

# 3. Test Fetching

message("\n--- Testing live RSS fetch ---")
# Use a known active and public account for testing, plus the newsroom.co.za handles
test_handles_fetch <- c("@Gargron@mastodon.social", "@index@www.newsroom.co.za", "@index@wwww.newsroom.co.za")

for (handle in test_handles_fetch) {
  message("\n----------------------------------------")
  message("Testing fetch for: ", handle)
  posts <- tryCatch({
    fetch_fediverse_posts(handle)
  }, error = function(e) {
    message("Error during fetch for ", handle, ": ", e$message)
    list()
  })
  
  message("Fetch result check for ", handle, ":")
  message("Total posts retrieved: ", length(posts))
  
  if (length(posts) > 0) {
    # Print the structure of the first post
    first_post <- posts[[1]]
    message("First Post Structure:")
    message("  UID: ", first_post$uid)
    message("  Datetime: ", first_post$datetime)
    message("  Source: ", first_post$source)
    message("  Sender: ", first_post$sender)
    message("  Title: ", first_post$title)
    message("  Body: ", first_post$body)
  } else {
    message("No posts retrieved for ", handle)
  }
}

# 4. Mock Fetching for @index@www.newsroom.co.za
message("\n----------------------------------------")
message("Testing MOCK fetch for: @index@www.newsroom.co.za")

mock_xml <- '<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>index</title>
    <link>https://www.newsroom.co.za/@index</link>
    <description>Public posts from @index@www.newsroom.co.za</description>
    <item>
      <title>New article published: South Africa\'s Energy Grid Resilience</title>
      <link>https://www.newsroom.co.za/@index/108392019382019</link>
      <pubDate>Thu, 21 May 2026 12:30:00 +0200</pubDate>
      <description>&lt;p&gt;We have just released our quarterly report on South Africa\'s energy grid resilience. &lt;a href="https://www.newsroom.co.za/reports/energy-grid"&gt;Read here&lt;/a&gt; for full analysis.&lt;/p&gt;</description>
    </item>
    <item>
      <title>Discussion on African Union Trade Agreements</title>
      <link>https://www.newsroom.co.za/@index/108391819382019</link>
      <pubDate>Wed, 20 May 2026 15:45:00 +0200</pubDate>
      <description>&lt;p&gt;Fascinating insights from the AU trade summit. The AfCFTA implementation is accelerating, but infrastructure challenges remain.&lt;/p&gt;</description>
    </item>
  </channel>
</rss>'

# We parse the mock xml directly using xml2 and simulate the actual parsing/scraping logic
xml_doc <- xml2::read_xml(mock_xml)
items <- xml2::xml_find_all(xml_doc, "//item")
records <- list()
for (item in items) {
  title <- xml2::xml_text(xml2::xml_find_first(item, "./title"))
  link <- xml2::xml_text(xml2::xml_find_first(item, "./link"))
  desc <- xml2::xml_text(xml2::xml_find_first(item, "./description"))
  date_str <- xml2::xml_text(xml2::xml_find_first(item, "./pubDate"))
  
  title <- stringr::str_trim(title)
  body <- clean_fediverse_html(desc)
  link <- stringr::str_trim(link)
  
  # Extract links from original description HTML
  target_link <- NULL
  if (!is.na(desc) && desc != "") {
      html_doc <- tryCatch({
          rvest::read_html(desc)
      }, error = function(e) NULL)
      
      if (!is.null(html_doc)) {
          a_nodes <- rvest::html_nodes(html_doc, "a")
          hrefs <- rvest::html_attr(a_nodes, "href")
          clean_links <- hrefs[!is.na(hrefs) & hrefs != ""]
          if (length(clean_links) > 0) {
              is_article <- vapply(clean_links, is_actual_article_link, logical(1))
              external_links <- clean_links[is_article]
              if (length(external_links) > 0) {
                  target_link <- external_links[1]
              }
          }
      }
  }
  
  url_to_save <- link
  if (!is.null(target_link)) {
      # Simulate scrape result for mock test
      scraped_content <- paste0("[MOCK SCRAPED CONTENT for ", target_link, " representing South Africa's Energy Grid Resilience report details]")
      body <- paste0("[Fediverse Update]: ", body, "\n\n[Scraped Article Content from ", target_link, "]:\n", scraped_content)
      url_to_save <- target_link
  }
  
  parsed_dt <- tryCatch({
    lubridate::parse_date_time(date_str, orders = c("a, d b Y H:M:S z", "Y-m-d H:M:S", "Y-m-dTH:M:Sz"))
  }, error = function(e) Sys.time())
  if (is.na(parsed_dt)) parsed_dt <- Sys.time()
  
  uid <- digest::digest(link, algo = "md5")
  
  records[[length(records) + 1]] <- list(
      uid = uid,
      datetime = as.character(parsed_dt),
      source = "Fediverse: @index@www.newsroom.co.za",
      sender = "index",
      title = title,
      url = url_to_save,
      body = body
  )
}

message("Mock parsing yielded ", length(records), " posts:")
print(jsonlite::toJSON(records, auto_unbox = TRUE, pretty = TRUE))

message("\n=== Diagnostic Tests Complete ===")
