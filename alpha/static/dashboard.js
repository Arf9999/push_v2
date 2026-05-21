// Dashboard State Management
let activeSearchSpace = "english";
let languagesChart = null;
let rawSearchResults = [];
let currentSearchResults = [];

// Auth & Personalization State
let currentUser = localStorage.getItem("username") || null;
let authToken = localStorage.getItem("token") || null;
let activeAuthTab = "login";
let activeWorkspaceTab = "saved-searches";
let notificationPollInterval = null;

// Initialize components when DOM loads
document.addEventListener("DOMContentLoaded", () => {
    initApp();
    setupEventListeners();
});

// Load stats and chart on initialization
async function initApp() {
    await fetchStats();
    await fetchEntitiesCloud();
    updateAuthUI();
}

// Helper for HTTP Headers
function getAuthHeaders() {
    return authToken ? { "Authorization": `Bearer ${authToken}` } : {};
}

// Bind event listeners
function setupEventListeners() {
    const searchForm = document.getElementById("search-form");
    const spaceEnglish = document.getElementById("space-english");
    const spaceMultilingual = document.getElementById("space-multilingual");
    const btnExportCsv = document.getElementById("btn-export-csv");
    const sensitivitySlider = document.getElementById("sensitivity-slider");
    const sensitivityValue = document.getElementById("sensitivity-value");

    // Auth Modal DOM Elements
    const btnShowAuth = document.getElementById("btn-show-auth");
    const btnCloseAuth = document.getElementById("btn-close-auth");
    const tabLogin = document.getElementById("tab-login");
    const tabRegister = document.getElementById("tab-register");
    const authForm = document.getElementById("auth-form");
    const btnLogout = document.getElementById("btn-logout");
    const btnBell = document.getElementById("btn-bell");
    const btnMarkRead = document.getElementById("btn-mark-read");
    const btnRunBatch = document.getElementById("btn-run-batch");
    const btnSaveSearch = document.getElementById("btn-save-search");

    // Workspace Tabs
    const tabSavedSearches = document.getElementById("tab-saved-searches");
    const tabRecentSearches = document.getElementById("tab-recent-searches");

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

    // Export CSV click listener
    if (btnExportCsv) {
        btnExportCsv.addEventListener("click", () => {
            exportCurrentResultsToCSV();
        });
    }

    // Sensitivity slider event listener
    if (sensitivitySlider) {
        sensitivitySlider.addEventListener("input", (e) => {
            const val = e.target.value;
            if (sensitivityValue) sensitivityValue.innerText = `${val}%`;
            
            // Re-render search results in real-time
            renderSearchResults(rawSearchResults);
        });
    }

    // Show Auth Modal
    if (btnShowAuth) {
        btnShowAuth.addEventListener("click", () => {
            document.getElementById("auth-error").style.display = "none";
            document.getElementById("auth-form").reset();
            setAuthTab("login");
            document.getElementById("auth-modal").style.display = "flex";
        });
    }

    // Close Auth Modal
    if (btnCloseAuth) {
        btnCloseAuth.addEventListener("click", () => {
            document.getElementById("auth-modal").style.display = "none";
        });
    }

    // Close modal on click outside content
    const authModal = document.getElementById("auth-modal");
    if (authModal) {
        authModal.addEventListener("click", (e) => {
            if (e.target === authModal) {
                authModal.style.display = "none";
            }
        });
    }

    // Auth Tab switching
    if (tabLogin) {
        tabLogin.addEventListener("click", () => setAuthTab("login"));
    }
    if (tabRegister) {
        tabRegister.addEventListener("click", () => setAuthTab("register"));
    }

    // Auth Form Submit
    if (authForm) {
        authForm.addEventListener("submit", (e) => {
            e.preventDefault();
            handleAuthSubmit();
        });
    }

    // Logout
    if (btnLogout) {
        btnLogout.addEventListener("click", () => {
            handleLogout();
        });
    }

    // Bell / Notifications Dropdown Toggle
    if (btnBell) {
        btnBell.addEventListener("click", (e) => {
            e.stopPropagation();
            const dropdown = document.getElementById("notifications-dropdown");
            const isVisible = dropdown.style.display === "flex";
            dropdown.style.display = isVisible ? "none" : "flex";
            if (!isVisible) {
                fetchNotifications();
            }
        });
    }

    // Close notifications dropdown on clicking outside
    document.addEventListener("click", () => {
        const dropdown = document.getElementById("notifications-dropdown");
        if (dropdown) dropdown.style.display = "none";
    });

    const notifDropdown = document.getElementById("notifications-dropdown");
    if (notifDropdown) {
        notifDropdown.addEventListener("click", (e) => {
            e.stopPropagation();
        });
    }

    // Mark all as read
    if (btnMarkRead) {
        btnMarkRead.addEventListener("click", () => {
            markAllNotificationsRead();
        });
    }

    // Run batch check
    if (btnRunBatch) {
        btnRunBatch.addEventListener("click", () => {
            triggerBatchCheck();
        });
    }

    // Save Search Click
    if (btnSaveSearch) {
        btnSaveSearch.addEventListener("click", () => {
            saveCurrentSearch();
        });
    }

    // Workspace Tabs
    if (tabSavedSearches) {
        tabSavedSearches.addEventListener("click", () => setWorkspaceTab("saved-searches"));
    }
    if (tabRecentSearches) {
        tabRecentSearches.addEventListener("click", () => setWorkspaceTab("recent-searches"));
    }
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
// Execute semantic search query
async function executeSearch() {
    const queryInput = document.getElementById("search-input");
    const query = queryInput.value.trim();
    if (!query) return;
    
    const resultsList = document.getElementById("results-list");
    const resultsCount = document.getElementById("results-count");
    const btnExportCsv = document.getElementById("btn-export-csv");
    
    // Reset save search star indicator
    const btnSaveSearch = document.getElementById("btn-save-search");
    if (btnSaveSearch) {
        btnSaveSearch.classList.remove("active");
        const starIcon = btnSaveSearch.querySelector("i");
        if (starIcon) {
            starIcon.className = "fa-regular fa-star";
        }
    }
    
    // Show spinner/loading state
    resultsCount.innerText = "Searching vectors...";
    if (btnExportCsv) btnExportCsv.style.display = "none";
    
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
        rawSearchResults = data.results || [];
        renderSearchResults(rawSearchResults);
        
        // Log search history asynchronously if logged in
        if (currentUser) {
            fetch("/api/history", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    ...getAuthHeaders()
                },
                body: JSON.stringify({
                    search_text: query,
                    space: activeSearchSpace
                })
            }).then(res => {
                if (res.ok) {
                    fetchRecentSearches();
                }
            }).catch(err => console.error("Error logging search history:", err));
        }
    } catch (err) {
        console.error("Error during search:", err);
        resultsCount.innerText = "Search error occurred";
        if (btnExportCsv) btnExportCsv.style.display = "none";
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
    const btnExportCsv = document.getElementById("btn-export-csv");
    const sensitivitySlider = document.getElementById("sensitivity-slider");
    
    resultsList.innerHTML = "";
    
    const sliderValue = sensitivitySlider ? parseFloat(sensitivitySlider.value) / 100 : 0.40;
    const filteredResults = (results || []).filter(rec => rec.similarity >= sliderValue);
    currentSearchResults = filteredResults;
    
    if (!results || results.length === 0) {
        if (btnExportCsv) btnExportCsv.style.display = "none";
        resultsCount.innerText = "0 matches found";
        resultsList.innerHTML = `
            <div class="empty-state">
                <i class="fa-solid fa-face-frown empty-icon"></i>
                <p>No matches found. Try refining your keywords or query idea.</p>
            </div>
        `;
        return;
    }
    
    if (filteredResults.length === 0) {
        if (btnExportCsv) btnExportCsv.style.display = "none";
        resultsCount.innerText = `0 matches above threshold (Threshold: ${Math.round(sliderValue * 100)}%)`;
        resultsList.innerHTML = `
            <div class="empty-state">
                <i class="fa-solid fa-sliders empty-icon"></i>
                <p>No matches found with similarity >= ${Math.round(sliderValue * 100)}%. Try lowering the sensitivity slider.</p>
            </div>
        `;
        return;
    }
    
    if (btnExportCsv) btnExportCsv.style.display = "flex";
    resultsCount.innerText = `Found ${filteredResults.length} matches (Threshold: ${Math.round(sliderValue * 100)}%)`;
    
    filteredResults.forEach(rec => {
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

// Export current search results to CSV
function exportCurrentResultsToCSV() {
    if (!currentSearchResults || currentSearchResults.length === 0) return;
    
    // Define headers
    const headers = [
        "UID",
        "Date",
        "Source",
        "Sender",
        "Title",
        "English Summary",
        "Original Summary",
        "Detected Language",
        "Content Type",
        "Topics",
        "Themes",
        "Keywords",
        "Cosine Similarity Score",
        "Resolved Entities"
    ];
    
    // Construct CSV lines
    const csvRows = [headers.join(",")];
    
    currentSearchResults.forEach(item => {
        const row = [
            item.uid || "",
            item.datetime || "",
            item.source || "",
            item.sender || "",
            item.title || "",
            item.summary || "",
            item.original_language_summary || "",
            item.detected_language || "",
            item.content_type || "",
            (item.topics || []).join(";"),
            (item.themes || []).join(";"),
            (item.keywords || []).join(";"),
            item.similarity !== undefined ? item.similarity.toFixed(4) : "",
            (item.entities || []).map(e => `${e.name}:${e.type}`).join(";")
        ];
        
        // Escape CSV values
        const escapedRow = row.map(val => {
            const strVal = String(val).replace(/"/g, '""');
            return `"${strVal}"`;
        });
        
        csvRows.push(escapedRow.join(","));
    });
    
    // Create blob and download
    const csvContent = "\uFEFF" + csvRows.join("\n"); // Add UTF-8 BOM
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    
    // Form filename with search term and timestamp
    const query = document.getElementById("search-input").value.trim().replace(/[^a-z0-9]/gi, '_').toLowerCase();
    const timestamp = new Date().toISOString().slice(0, 10);
    link.setAttribute("href", url);
    link.setAttribute("download", `narrative_search_${query || "results"}_${timestamp}.csv`);
    link.style.visibility = "hidden";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Floating Toast Notification
function showToast(message, type = "success") {
    let container = document.getElementById("toast-container");
    if (!container) {
        container = document.createElement("div");
        container.id = "toast-container";
        Object.assign(container.style, {
            position: "fixed",
            bottom: "24px",
            right: "24px",
            display: "flex",
            flexDirection: "column",
            gap: "8px",
            zIndex: "9999",
            pointerEvents: "none"
        });
        document.body.appendChild(container);
    }
    
    const toast = document.createElement("div");
    toast.className = `toast glass-panel animate-fade-in`;
    Object.assign(toast.style, {
        background: type === "error" ? "rgba(239, 68, 68, 0.95)" : "rgba(16, 185, 129, 0.95)",
        color: "#ffffff",
        padding: "12px 20px",
        borderRadius: "8px",
        fontSize: "13px",
        fontWeight: "500",
        backdropFilter: "blur(8px)",
        boxShadow: "0 8px 32px 0 rgba(0, 0, 0, 0.3)",
        border: "1px solid rgba(255, 255, 255, 0.1)",
        display: "flex",
        alignItems: "center",
        gap: "10px",
        pointerEvents: "auto",
        transition: "opacity 0.3s ease-out, transform 0.3s ease-out",
        opacity: "0",
        transform: "translateY(20px)"
    });
    
    const icon = document.createElement("i");
    icon.className = type === "error" ? "fa-solid fa-triangle-exclamation" : "fa-solid fa-circle-check";
    toast.appendChild(icon);
    
    const textNode = document.createElement("span");
    textNode.innerText = message;
    toast.appendChild(textNode);
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = "1";
        toast.style.transform = "translateY(0)";
    }, 10);
    
    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateY(-20px)";
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 4000);
}

// Auth UI State Toggle
function updateAuthUI() {
    currentUser = localStorage.getItem("username") || null;
    authToken = localStorage.getItem("token") || null;
    
    const btnShowAuth = document.getElementById("btn-show-auth");
    const userProfileWidget = document.getElementById("user-profile-widget");
    const profileUsername = document.getElementById("profile-username");
    const personalizationPanel = document.getElementById("personalization-panel");
    const btnSaveSearch = document.getElementById("btn-save-search");
    
    if (currentUser && authToken) {
        if (btnShowAuth) btnShowAuth.style.display = "none";
        if (userProfileWidget) userProfileWidget.style.display = "flex";
        if (profileUsername) profileUsername.innerText = currentUser;
        if (personalizationPanel) personalizationPanel.style.display = "block";
        if (btnSaveSearch) btnSaveSearch.style.display = "block";
        
        setWorkspaceTab(activeWorkspaceTab);
        fetchNotifications();
        
        if (!notificationPollInterval) {
            notificationPollInterval = setInterval(fetchNotificationsPoll, 30000);
        }
    } else {
        if (btnShowAuth) btnShowAuth.style.display = "block";
        if (userProfileWidget) userProfileWidget.style.display = "none";
        if (personalizationPanel) personalizationPanel.style.display = "none";
        if (btnSaveSearch) btnSaveSearch.style.display = "none";
        
        if (notificationPollInterval) {
            clearInterval(notificationPollInterval);
            notificationPollInterval = null;
        }
        
        const badge = document.getElementById("notification-badge");
        if (badge) {
            badge.innerText = "0";
            badge.style.display = "none";
        }
        const notifList = document.getElementById("notifications-list");
        if (notifList) {
            notifList.innerHTML = `<div class="empty-notifications">No new notifications</div>`;
        }
    }
}

let knownNotificationIds = new Set();

// Fetch Notifications from API
async function fetchNotifications(isPoll = false) {
    if (!currentUser) return;
    try {
        const response = await fetch("/api/notifications", {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error("Failed to fetch notifications");
        
        const data = await response.json();
        const notifications = data.notifications || [];
        
        const unreadCount = notifications.filter(n => !n.is_read).length;
        const badge = document.getElementById("notification-badge");
        if (badge) {
            if (unreadCount > 0) {
                badge.innerText = unreadCount;
                badge.style.display = "block";
            } else {
                badge.innerText = "0";
                badge.style.display = "none";
            }
        }
        
        if (isPoll && notifications.length > 0) {
            notifications.forEach(n => {
                if (!n.is_read && !knownNotificationIds.has(n.id)) {
                    showToast(`Alert: New articles match your saved search: "${n.search_text}"`);
                }
            });
        }
        
        notifications.forEach(n => knownNotificationIds.add(n.id));
        
        const notifList = document.getElementById("notifications-list");
        if (notifList) {
            if (notifications.length === 0) {
                notifList.innerHTML = `<div class="empty-notifications">No notifications yet</div>`;
            } else {
                notifList.innerHTML = "";
                notifications.forEach(n => {
                    const item = document.createElement("div");
                    item.className = `notification-item ${n.is_read ? "" : "unread"}`;
                    
                    const timeStr = new Date(n.created_at + "Z").toLocaleString();
                    
                    item.innerHTML = `
                        <div class="notification-item-header">
                            <span class="notification-item-query">${n.search_text}</span>
                            <span>${timeStr}</span>
                        </div>
                        <div class="notification-item-body">
                            Found ${n.new_results_count} new match${n.new_results_count > 1 ? "es" : ""}! 
                            Newest: <strong>${n.newest_title}</strong>
                        </div>
                    `;
                    
                    item.addEventListener("click", () => {
                        const searchInput = document.getElementById("search-input");
                        if (searchInput) {
                            searchInput.value = n.search_text;
                            executeSearch();
                        }
                    });
                    notifList.appendChild(item);
                });
            }
        }
    } catch (err) {
        console.error("Error fetching notifications:", err);
    }
}

function fetchNotificationsPoll() {
    fetchNotifications(true);
}

// Auth modal tab switcher
function setAuthTab(tab) {
    activeAuthTab = tab;
    const tabLogin = document.getElementById("tab-login");
    const tabRegister = document.getElementById("tab-register");
    const btnAuthSubmit = document.getElementById("btn-auth-submit");
    const authError = document.getElementById("auth-error");
    
    if (tabLogin) tabLogin.classList.toggle("active", tab === "login");
    if (tabRegister) tabRegister.classList.toggle("active", tab === "register");
    
    if (btnAuthSubmit) {
        btnAuthSubmit.querySelector("span").innerText = tab === "login" ? "Sign In" : "Register";
    }
    if (authError) {
        authError.style.display = "none";
        authError.innerText = "";
    }
}

// Submit Login or Register form
async function handleAuthSubmit() {
    const usernameInput = document.getElementById("auth-username");
    const passwordInput = document.getElementById("auth-password");
    const authError = document.getElementById("auth-error");
    
    const username = usernameInput.value.trim();
    const password = passwordInput.value;
    
    if (!username || !password) {
        if (authError) {
            authError.innerText = "All fields are required";
            authError.style.display = "block";
        }
        return;
    }
    
    const endpoint = activeAuthTab === "login" ? "/api/auth/login" : "/api/auth/register";
    
    try {
        const response = await fetch(endpoint, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ username, password })
        });
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.detail || "Authentication request failed");
        }
        
        const data = await response.json();
        
        if (activeAuthTab === "login") {
            localStorage.setItem("token", data.token);
            localStorage.setItem("username", data.username);
            
            document.getElementById("auth-modal").style.display = "none";
            updateAuthUI();
            showToast(`Welcome back, ${data.username}!`);
        } else {
            showToast("Registration successful! Logging in...");
            const loginResp = await fetch("/api/auth/login", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ username, password })
            });
            if (loginResp.ok) {
                const loginData = await loginResp.json();
                localStorage.setItem("token", loginData.token);
                localStorage.setItem("username", loginData.username);
                document.getElementById("auth-modal").style.display = "none";
                updateAuthUI();
            } else {
                setAuthTab("login");
            }
        }
    } catch (err) {
        if (authError) {
            authError.innerText = err.message;
            authError.style.display = "block";
        }
    }
}

// Log out user session
function handleLogout() {
    localStorage.removeItem("username");
    localStorage.removeItem("token");
    updateAuthUI();
    showToast("Logged out successfully");
}

// Tab switching inside Personal Workspace panel
function setWorkspaceTab(tab) {
    activeWorkspaceTab = tab;
    const tabSavedSearches = document.getElementById("tab-saved-searches");
    const tabRecentSearches = document.getElementById("tab-recent-searches");
    const savedSearchesList = document.getElementById("saved-searches-list");
    const recentSearchesList = document.getElementById("recent-searches-list");
    
    if (tabSavedSearches) tabSavedSearches.classList.toggle("active", tab === "saved-searches");
    if (tabRecentSearches) tabRecentSearches.classList.toggle("active", tab === "recent-searches");
    
    if (tab === "saved-searches") {
        if (savedSearchesList) savedSearchesList.style.display = "flex";
        if (recentSearchesList) recentSearchesList.style.display = "none";
        fetchSavedSearches();
    } else {
        if (savedSearchesList) savedSearchesList.style.display = "none";
        if (recentSearchesList) recentSearchesList.style.display = "flex";
        fetchRecentSearches();
    }
}

// Fetch user's saved searches from SQLite
async function fetchSavedSearches() {
    if (!currentUser) return;
    const listContainer = document.getElementById("saved-searches-list");
    if (!listContainer) return;
    
    try {
        const response = await fetch("/api/saved-searches", {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error("Failed to fetch saved searches");
        
        const data = await response.json();
        const savedList = data.saved_searches || [];
        
        if (savedList.length === 0) {
            listContainer.innerHTML = `<p class="loading-placeholder">No saved searches yet.</p>`;
            return;
        }
        
        listContainer.innerHTML = "";
        savedList.forEach(s => {
            const item = document.createElement("div");
            item.className = "workspace-item";
            
            item.innerHTML = `
                <div class="workspace-item-info">
                    <span class="workspace-item-title" title="${s.search_text}">${s.search_text}</span>
                    <div class="workspace-item-meta">
                        <span><i class="fa-solid fa-flag"></i> ${s.space}</span>
                        <span><i class="fa-solid fa-sliders"></i> ${Math.round(s.threshold * 100)}%</span>
                    </div>
                </div>
                <button class="btn-delete-search" data-id="${s.id}" title="Delete Saved Search">
                    <i class="fa-solid fa-trash"></i>
                </button>
            `;
            
            item.addEventListener("click", (e) => {
                if (e.target.closest(".btn-delete-search")) return;
                
                const searchInput = document.getElementById("search-input");
                if (searchInput) {
                    searchInput.value = s.search_text;
                    setActiveSpace(s.space);
                    const slider = document.getElementById("sensitivity-slider");
                    const valueDisplay = document.getElementById("sensitivity-value");
                    if (slider) {
                        slider.value = Math.round(s.threshold * 100);
                        if (valueDisplay) valueDisplay.innerText = `${slider.value}%`;
                    }
                    executeSearch();
                }
            });
            
            const deleteBtn = item.querySelector(".btn-delete-search");
            deleteBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                deleteSavedSearch(s.id);
            });
            
            listContainer.appendChild(item);
        });
    } catch (err) {
        console.error("Error loading saved searches:", err);
        listContainer.innerHTML = `<p class="loading-placeholder">Error loading saved searches.</p>`;
    }
}

async function deleteSavedSearch(id) {
    if (!confirm("Are you sure you want to delete this saved search?")) return;
    try {
        const response = await fetch(`/api/saved-searches/${id}`, {
            method: "DELETE",
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error("Failed to delete saved search");
        
        showToast("Saved search deleted successfully");
        fetchSavedSearches();
    } catch (err) {
        console.error("Error deleting saved search:", err);
        showToast(err.message, "error");
    }
}

// Fetch user's search history from SQLite
async function fetchRecentSearches() {
    if (!currentUser) return;
    const listContainer = document.getElementById("recent-searches-list");
    if (!listContainer) return;
    
    try {
        const response = await fetch("/api/history", {
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error("Failed to fetch search history");
        
        const data = await response.json();
        const historyList = data.history || [];
        
        if (historyList.length === 0) {
            listContainer.innerHTML = `<p class="loading-placeholder">No recent searches.</p>`;
            return;
        }
        
        listContainer.innerHTML = "";
        historyList.forEach(h => {
            const item = document.createElement("div");
            item.className = "workspace-item";
            
            const timeStr = new Date(h.searched_at + "Z").toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            
            item.innerHTML = `
                <div class="workspace-item-info">
                    <span class="workspace-item-title" title="${h.search_text}">${h.search_text}</span>
                    <div class="workspace-item-meta">
                        <span><i class="fa-solid fa-flag"></i> ${h.space}</span>
                        <span>${timeStr}</span>
                    </div>
                </div>
            `;
            
            item.addEventListener("click", () => {
                const searchInput = document.getElementById("search-input");
                if (searchInput) {
                    searchInput.value = h.search_text;
                    setActiveSpace(h.space);
                    executeSearch();
                }
            });
            
            listContainer.appendChild(item);
        });
    } catch (err) {
        console.error("Error loading search history:", err);
        listContainer.innerHTML = `<p class="loading-placeholder">Error loading search history.</p>`;
    }
}

// Save the current active query with options
async function saveCurrentSearch() {
    if (!currentUser) {
        showToast("Please log in to save searches", "error");
        return;
    }
    
    const searchInput = document.getElementById("search-input");
    const query = searchInput.value.trim();
    if (!query) {
        showToast("Please execute or enter a query to save", "error");
        return;
    }
    
    const slider = document.getElementById("sensitivity-slider");
    const threshold = slider ? parseFloat(slider.value) / 100 : 0.40;
    
    try {
        const response = await fetch("/api/saved-searches", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                ...getAuthHeaders()
            },
            body: JSON.stringify({
                search_text: query,
                space: activeSearchSpace,
                threshold: threshold
            })
        });
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.detail || "Failed to save search");
        }
        
        showToast("Search saved successfully!");
        
        const btnSaveSearch = document.getElementById("btn-save-search");
        if (btnSaveSearch) {
            btnSaveSearch.classList.add("active");
            const starIcon = btnSaveSearch.querySelector("i");
            if (starIcon) {
                starIcon.className = "fa-solid fa-star";
            }
        }
        
        fetchSavedSearches();
    } catch (err) {
        console.error("Error saving search:", err);
        showToast(err.message, "error");
    }
}

async function markAllNotificationsRead() {
    if (!currentUser) return;
    try {
        const response = await fetch("/api/notifications/read", {
            method: "POST",
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error("Failed to mark notifications read");
        
        showToast("All notifications marked as read");
        fetchNotifications();
    } catch (err) {
        console.error("Error reading notifications:", err);
        showToast(err.message, "error");
    }
}

async function triggerBatchCheck() {
    if (!currentUser) return;
    const btnRunBatch = document.getElementById("btn-run-batch");
    const originalHtml = btnRunBatch.innerHTML;
    
    btnRunBatch.disabled = true;
    btnRunBatch.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Checking vector database...`;
    
    try {
        const response = await fetch("/api/notifications/check", {
            method: "POST",
            headers: getAuthHeaders()
        });
        if (!response.ok) throw new Error("Batch check failed");
        
        showToast("Batch check completed successfully!");
        
        await fetchNotifications();
        await fetchSavedSearches();
    } catch (err) {
        console.error("Error running batch check:", err);
        showToast(err.message, "error");
    } finally {
        btnRunBatch.disabled = false;
        btnRunBatch.innerHTML = originalHtml;
    }
}

