// Dashboard State Management
let activeSearchSpace = "english";
let languagesChart = null;

// Initialize components when DOM loads
document.addEventListener("DOMContentLoaded", () => {
    initApp();
    setupEventListeners();
});

// Load stats and chart on initialization
async function initApp() {
    await fetchStats();
    await fetchEntitiesCloud();
}

// Bind event listeners
function setupEventListeners() {
    const searchForm = document.getElementById("search-form");
    const spaceEnglish = document.getElementById("space-english");
    const spaceMultilingual = document.getElementById("space-multilingual");

    // Form Submission
    searchForm.addEventListener("submit", (e) => {
        e.preventDefault();
        executeSearch();
    });

    // Space Toggle listeners
    spaceEnglish.addEventListener("click", () => {
        setActiveSpace("english");
    });

    spaceMultilingual.addEventListener("click", () => {
        setActiveSpace("multilingual");
    });
}

// Manage Toggle Buttons
function setActiveSpace(space) {
    activeSearchSpace = space;
    document.getElementById("space-english").classList.toggle("active", space === "english");
    document.getElementById("space-multilingual").classList.toggle("active", space === "multilingual");
    
    // Auto re-execute search if input is populated
    const query = document.getElementById("search-input").value.trim();
    if (query) {
        executeSearch();
    }
}

// Fetch stats and update UI + Chart
async function fetchStats() {
    try {
        const response = await fetch("/api/stats");
        if (!response.ok) throw new Error("Failed to fetch analytics metrics");
        
        const data = await response.json();
        
        // Update cards
        document.getElementById("val-total").innerText = data.total_articles.toLocaleString();
        document.getElementById("val-languages").innerText = data.languages.length;
        document.getElementById("val-sources").innerText = data.sources.length;
        document.getElementById("val-marketing").innerText = data.marketing_count.toLocaleString();
        
        // Render or update Languages Donut Chart
        renderLanguagesChart(data.languages);
    } catch (err) {
        console.error("Error fetching statistics:", err);
    }
}

// Render Languages Chart using Chart.js
function renderLanguagesChart(languageData) {
    const ctx = document.getElementById("languages-chart").getContext("2d");
    
    const labels = languageData.map(l => l.lang.toUpperCase());
    const counts = languageData.map(l => l.count);
    
    // Emerald green and violet gradients for dark mode theme
    const colors = [
        "#10B981", // Emerald
        "#8B5CF6", // Violet
        "#3B82F6", // Blue
        "#F59E0B", // Amber
        "#EC4899", // Pink
        "#EF4444"  // Red
    ];
    
    if (languagesChart) {
        languagesChart.destroy();
    }
    
    languagesChart = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: labels,
            datasets: [{
                data: counts,
                backgroundColor: colors.slice(0, labels.length),
                borderWidth: 1,
                borderColor: "rgba(255, 255, 255, 0.08)"
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "right",
                    labels: {
                        color: "#9CA3AF",
                        font: {
                            family: "Outfit",
                            size: 11
                        }
                    }
                }
            },
            cutout: "70%"
        }
    });
}

// Fetch and render top deduplicated entities
async function fetchEntitiesCloud() {
    try {
        const response = await fetch("/api/entities");
        if (!response.ok) throw new Error("Failed to fetch entity mappings");
        
        const data = await response.json();
        const cloudContainer = document.getElementById("entity-cloud");
        cloudContainer.innerHTML = "";
        
        if (!data.entities || data.entities.length === 0) {
            cloudContainer.innerHTML = "<p class='loading-placeholder'>No entities resolved yet.</p>";
            return;
        }
        
        // Show top 25 entities in cloud
        const topEntities = data.entities.slice(0, 25);
        
        topEntities.forEach(ent => {
            const item = document.createElement("div");
            item.className = "entity-cloud-item";
            
            const dotClass = getDotClassForType(ent.type);
            
            item.innerHTML = `
                <span class="entity-type-dot ${dotClass}"></span>
                <span class="entity-name">${ent.canonical_name}</span>
                <span class="entity-count">${ent.occurrence_count}</span>
            `;
            
            // Clicking entity in cloud triggers search
            item.addEventListener("click", () => {
                triggerFilter(ent.canonical_name);
            });
            
            cloudContainer.appendChild(item);
        });
    } catch (err) {
        console.error("Error loading entity cloud:", err);
        document.getElementById("entity-cloud").innerHTML = "<p class='loading-placeholder'>Error loading cloud.</p>";
    }
}

// Entity type dot mapper
function getDotClassForType(type) {
    const t = type.toUpperCase();
    if (t === "PERSON") return "dot-person";
    if (t === "ORG" || t === "ORGANIZATION") return "dot-org";
    if (t === "GPE") return "dot-gpe";
    if (t === "LOC") return "dot-loc";
    return "dot-org";
}

// Helper to fill search bar and execute query
function triggerFilter(value) {
    const input = document.getElementById("search-input");
    input.value = value;
    executeSearch();
}

// Execute semantic search query
async function executeSearch() {
    const queryInput = document.getElementById("search-input");
    const query = queryInput.value.trim();
    if (!query) return;
    
    const resultsList = document.getElementById("results-list");
    const resultsCount = document.getElementById("results-count");
    
    // Show spinner/loading state
    resultsCount.innerText = "Searching vectors...";
    resultsList.innerHTML = `
        <div class="empty-state">
            <i class="fa-solid fa-circle-notch fa-spin empty-icon"></i>
            <p>Searching DuckDB vector space using local array dot products...</p>
        </div>
    `;
    
    try {
        const url = `/api/search?q=${encodeURIComponent(query)}&space=${activeSearchSpace}&limit=20`;
        const response = await fetch(url);
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || "Query failed");
        }
        
        const data = await response.json();
        renderSearchResults(data.results);
    } catch (err) {
        console.error("Error during search:", err);
        resultsCount.innerText = "Search error occurred";
        resultsList.innerHTML = `
            <div class="empty-state" style="border-color: #ef4444;">
                <i class="fa-solid fa-triangle-exclamation empty-icon" style="color: #ef4444;"></i>
                <p style="color: #ef4444;">Search failed: ${err.message}</p>
            </div>
        `;
    }
}

// Render results
function renderSearchResults(results) {
    const resultsList = document.getElementById("results-list");
    const resultsCount = document.getElementById("results-count");
    
    resultsList.innerHTML = "";
    
    if (!results || results.length === 0) {
        resultsCount.innerText = "0 matches found";
        resultsList.innerHTML = `
            <div class="empty-state">
                <i class="fa-solid fa-face-frown empty-icon"></i>
                <p>No matches found. Try refining your keywords or query idea.</p>
            </div>
        `;
        return;
    }
    
    resultsCount.innerText = `Found ${results.length} matches sorted by relevance`;
    
    results.forEach(rec => {
        const card = document.createElement("article");
        card.className = "article-card glass-panel animate-fade-in";
        
        const similarityPct = Math.round(rec.similarity * 100);
        
        // Setup tags
        let topicsHtml = rec.topics.map(t => `<span class="tag tag-topic">${t}</span>`).join("");
        let themesHtml = rec.themes.map(t => `<span class="tag tag-theme">${t}</span>`).join("");
        
        // Render entities from rec.entities list
        let entitiesHtml = "";
        if (rec.entities && rec.entities.length > 0) {
            entitiesHtml = rec.entities.map(e => `
                <span class="tag tag-entity" onclick="triggerFilter('${e.name}')">
                    <i class="fa-solid fa-tag"></i> ${e.name}
                </span>
            `).join("");
        }
        
        // Card Body structure
        card.innerHTML = `
            <div class="article-meta">
                <div class="meta-left">
                    <span class="source-badge">${rec.source}</span>
                    <span class="lang-badge">${rec.detected_language}</span>
                    <span class="date-text">${rec.datetime.split(" ")[0]}</span>
                </div>
                <div class="similarity-badge">
                    <span>${similarityPct}% match</span>
                    <div class="similarity-bar">
                        <div class="similarity-fill" style="width: ${similarityPct}%"></div>
                    </div>
                </div>
            </div>
            
            <h3 class="article-title">${rec.title}</h3>
            
            <div class="article-summary-box">
                <div class="summary-heading">
                    <h4 id="summary-title-${rec.uid}">English Summary</h4>
                    ${rec.detected_language !== "en" && rec.original_language_summary ? 
                      `<button class="summary-toggle-btn" id="toggle-btn-${rec.uid}" data-state="en">Show Original</button>` : ""}
                </div>
                <p class="summary-text" id="summary-txt-${rec.uid}">${rec.summary}</p>
            </div>
            
            <div class="tags-row">
                ${topicsHtml}
                ${themesHtml}
                ${entitiesHtml}
            </div>
        `;
        
        resultsList.appendChild(card);
        
        // Set up Summary Toggle handler if multilingual
        if (rec.detected_language !== "en" && rec.original_language_summary) {
            const toggleBtn = card.querySelector(`#toggle-btn-${rec.uid}`);
            const summaryText = card.querySelector(`#summary-txt-${rec.uid}`);
            const summaryTitle = card.querySelector(`#summary-title-${rec.uid}`);
            
            toggleBtn.addEventListener("click", () => {
                if (toggleBtn.dataset.state === "en") {
                    summaryText.innerText = rec.original_language_summary;
                    summaryTitle.innerText = "Original Language Summary";
                    toggleBtn.innerText = "Show English";
                    toggleBtn.dataset.state = "orig";
                } else {
                    summaryText.innerText = rec.summary;
                    summaryTitle.innerText = "English Summary";
                    toggleBtn.innerText = "Show Original";
                    toggleBtn.dataset.state = "en";
                }
            });
        }
    });
}

