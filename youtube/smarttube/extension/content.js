/**
 * content.js — SmartTube Content Script
 * 
 * Injected on youtube.com/results* pages.
 * Handles:
 * 1. Injecting the "✨ Analyze Videos" floating / sticky action button.
 * 2. Scraping visible video metadata cleanly from the YouTube DOM using selectors.js.
 * 3. Messaging background service worker to fetch AI/Scored ranking.
 * 4. Rendering the SmartTube ranking overlay panel and "Save My Time" summary.
 */

(function () {
  const S = window.SMARTTUBE_SELECTORS;
  let isAnalyzing = false;

  // Helpers to parse YouTube duration, views, relative dates
  function parseDurationToSeconds(durationStr) {
    if (!durationStr) return 0;
    const parts = durationStr.trim().split(":").map(Number);
    if (parts.length === 2) {
      return parts[0] * 60 + parts[1]; // mm:ss
    } else if (parts.length === 3) {
      return parts[0] * 3600 + parts[1] * 60 + parts[2]; // hh:mm:ss
    }
    return 0;
  }

  function parseViews(viewStr) {
    if (!viewStr) return 0;
    const clean = viewStr.toLowerCase().replace(/views?/g, "").replace(/,/g, "").trim();
    if (clean.includes("m")) {
      return parseFloat(clean) * 1_000_000;
    }
    if (clean.includes("k")) {
      return parseFloat(clean) * 1_000;
    }
    if (clean.includes("b")) {
      return parseFloat(clean) * 1_000_000_000;
    }
    return parseInt(clean, 10) || 0;
  }

  function getSearchQuery() {
    const urlParams = new URLSearchParams(window.location.search);
    const qFromUrl = urlParams.get("search_query");
    if (qFromUrl) return qFromUrl.trim();

    const input = document.querySelector(S.SEARCH_INPUT);
    return input ? input.value.trim() : "";
  }

  function scrapeVideoCards() {
    const cards = Array.from(document.querySelectorAll(S.VIDEO_CARD));
    const videos = [];

    cards.forEach((card, index) => {
      try {
        const titleLink = card.querySelector(S.TITLE_LINK);
        if (!titleLink) return;

        const href = titleLink.getAttribute("href") || "";
        const videoIdMatch = href.match(/v=([a-zA-Z0-9_-]{11})/);
        const videoId = videoIdMatch ? videoIdMatch[1] : `dom-idx-${index}`;

        // Extract Title
        const title = (titleLink.textContent || titleLink.getAttribute("title") || "").trim();
        if (!title) return;

        // Extract Channel
        const channelEl = card.querySelector(S.CHANNEL_NAME);
        const channel = channelEl ? channelEl.textContent.trim() : "Unknown Channel";

        // Extract Description Snippet
        const descEl = card.querySelector(S.DESCRIPTION);
        const description = descEl ? descEl.textContent.trim() : "";

        // Extract Duration
        const durationEl = card.querySelector(S.DURATION);
        const durationStr = durationEl ? durationEl.textContent.trim() : "0:00";
        const durationSec = parseDurationToSeconds(durationStr);

        // Metadata line (views + relative time)
        const metaItems = card.querySelectorAll(S.METADATA_LINE);
        let viewCountStr = "0 views";
        let publishedTimeStr = "recently";

        if (metaItems.length >= 1) {
          viewCountStr = metaItems[0].textContent.trim();
        }
        if (metaItems.length >= 2) {
          publishedTimeStr = metaItems[1].textContent.trim();
        }

        const views = parseViews(viewCountStr);

        // Thumbnail
        const thumbImg = card.querySelector(S.THUMBNAIL_IMG);
        const thumbnail = thumbImg ? (thumbImg.src || thumbImg.getAttribute("src") || `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg`) : `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg`;

        videos.push({
          id: videoId,
          title,
          channel,
          description,
          duration_seconds: durationSec,
          duration_formatted: durationStr,
          views,
          views_formatted: viewCountStr,
          published_text: publishedTimeStr,
          thumbnail_url: thumbnail,
          url: `https://www.youtube.com/watch?v=${videoId}`,
          original_rank: index + 1
        });
      } catch (err) {
        console.warn("[SmartTube] Error parsing video card:", err);
      }
    });

    return videos;
  }

  // UI Injection: Top Action Bar Button
  function injectAnalyzeButton() {
    if (document.getElementById(S.ANALYZE_BTN_ID)) return;

    const btnWrapper = document.createElement("div");
    btnWrapper.id = S.ANALYZE_BTN_ID;
    btnWrapper.className = "smarttube-btn-wrapper";

    const btn = document.createElement("button");
    btn.className = "smarttube-action-btn";
    btn.innerHTML = `<span class="smarttube-sparkle">✨</span> <span class="smarttube-btn-text">Analyze & Re-rank</span>`;
    
    btn.addEventListener("click", onAnalyzeClick);
    btnWrapper.appendChild(btn);

    document.body.appendChild(btnWrapper);
  }

  async function onAnalyzeClick() {
    if (isAnalyzing) return;
    const query = getSearchQuery();

    if (!query) {
      alert("SmartTube: Please enter a search query on YouTube first!");
      return;
    }

    const videos = scrapeVideoCards();
    if (videos.length === 0) {
      alert("SmartTube: No search result videos found on page to analyze. Make sure results are loaded.");
      return;
    }

    setLoadingState(true);

    try {
      // Send message to background service worker
      const response = await chrome.runtime.sendMessage({
        type: "RANK_VIDEOS",
        payload: {
          query,
          videos
        }
      });

      if (!response || !response.success) {
        throw new Error(response ? response.error : "Failed to get response from SmartTube backend.");
      }

      renderResultsPanel(query, response.data);
    } catch (err) {
      console.error("[SmartTube] Ranking request failed:", err);
      alert(`SmartTube Analysis Failed: ${err.message}\nMake sure the FastAPI backend is running on http://127.0.0.1:8000`);
    } finally {
      setLoadingState(false);
    }
  }

  function setLoadingState(loading) {
    isAnalyzing = loading;
    const btn = document.querySelector(`#${S.ANALYZE_BTN_ID} button`);
    if (!btn) return;

    if (loading) {
      btn.disabled = true;
      btn.innerHTML = `<div class="smarttube-spinner"></div> Analyzing ${scrapeVideoCards().length} videos...`;
    } else {
      btn.disabled = false;
      btn.innerHTML = `<span class="smarttube-sparkle">✨</span> <span class="smarttube-btn-text">Analyze & Re-rank</span>`;
    }
  }

  function formatTime(totalSeconds) {
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    return `${minutes} mins`;
  }

  function renderResultsPanel(query, rankResult) {
    let panel = document.getElementById(S.PANEL_ID);
    if (!panel) {
      panel = document.createElement("div");
      panel.id = S.PANEL_ID;
      panel.className = "smarttube-panel-container";
      document.body.appendChild(panel);
    }

    const { results, summary } = rankResult;

    const highlyRelevantCount = summary.tier_counts["🔥 Highly Relevant"] || 0;
    const relevantCount = summary.tier_counts["✅ Relevant"] || 0;
    const otherCount = summary.tier_counts["📌 Other"] || 0;
    const totalWatchTimeFormatted = formatTime(summary.total_watch_time_seconds || 0);

    let cardsHtml = results.map((v, i) => {
      let badgeClass = "badge-other";
      if (v.label.includes("Highly")) badgeClass = "badge-high";
      else if (v.label.includes("Relevant")) badgeClass = "badge-medium";

      const scorePct = Math.round(v.final_score * 100);

      return `
        <div class="st-video-card" data-video-id="${v.id}">
          <div class="st-rank-badge">#${i + 1}</div>
          <div class="st-thumb-wrap">
            <a href="${v.url}" target="_blank">
              <img src="${v.thumbnail_url}" alt="${v.title}" class="st-thumb-img" />
              <span class="st-duration">${v.duration_formatted}</span>
            </a>
          </div>
          <div class="st-info-wrap">
            <div class="st-title-row">
              <a href="${v.url}" target="_blank" class="st-video-title" title="${v.title}">${v.title}</a>
            </div>
            <div class="st-meta-row">
              <span class="st-channel">${v.channel}</span> • 
              <span class="st-views">${v.views_formatted}</span> • 
              <span class="st-date">${v.published_text}</span>
            </div>
            <div class="st-score-row">
              <span class="st-badge ${badgeClass}">${v.label}</span>
              <span class="st-score-pill">Score: <strong>${scorePct}%</strong></span>
              <span class="st-orig-rank">Original: #${v.original_rank}</span>
            </div>
            <div class="st-explanation">
              💡 <em>${v.explanation}</em>
            </div>
          </div>
        </div>
      `;
    }).join("");

    panel.innerHTML = `
      <div class="smarttube-panel-backdrop"></div>
      <div class="smarttube-panel-modal">
        <div class="smarttube-header">
          <div class="st-header-title">
            <span class="st-logo-icon">✨</span>
            <div>
              <h3>SmartTube Relevance Re-Ranking</h3>
              <p class="st-subtitle">Query: "<strong>${query}</strong>" (${results.length} videos analyzed)</p>
            </div>
          </div>
          <button class="st-close-btn" id="st-close-panel">&times;</button>
        </div>

        <!-- Save My Time Summary Bar -->
        <div class="st-summary-bar">
          <div class="st-summary-item">
            <span class="st-summary-val">${results.length}</span>
            <span class="st-summary-label">Analyzed</span>
          </div>
          <div class="st-summary-item st-high-highlight">
            <span class="st-summary-val">🔥 ${highlyRelevantCount}</span>
            <span class="st-summary-label">Top Tier</span>
          </div>
          <div class="st-summary-item">
            <span class="st-summary-val">✅ ${relevantCount}</span>
            <span class="st-summary-label">Relevant</span>
          </div>
          <div class="st-summary-item">
            <span class="st-summary-val">📌 ${otherCount}</span>
            <span class="st-summary-label">Other</span>
          </div>
          <div class="st-summary-item">
            <span class="st-summary-val">⏱️ ${totalWatchTimeFormatted}</span>
            <span class="st-summary-label">Total Time</span>
          </div>
        </div>

        <div class="st-results-list">
          ${cardsHtml}
        </div>
      </div>
    `;

    document.getElementById("st-close-panel").addEventListener("click", () => {
      panel.classList.remove("active");
    });
    panel.querySelector(".smarttube-panel-backdrop").addEventListener("click", () => {
      panel.classList.remove("active");
    });

    panel.classList.add("active");
  }

  // Initialize observer for SPA navigation on YouTube
  function init() {
    injectAnalyzeButton();

    // YouTube is a Single Page Application (SPA), listen to history/navigation
    window.addEventListener("yt-navigate-finish", () => {
      if (window.location.pathname.startsWith("/results")) {
        injectAnalyzeButton();
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
