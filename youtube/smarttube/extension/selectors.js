/**
 * selectors.js — SmartTube DOM Selector Configuration
 *
 * ALL YouTube DOM selectors live here. When YouTube updates its markup,
 * this is the ONLY file that needs changing. Each selector is annotated
 * with what it targets and a fallback strategy.
 *
 * Loaded as a plain script BEFORE content.js via manifest content_scripts order.
 */

// Expose as a global so content.js can reference window.SMARTTUBE_SELECTORS
window.SMARTTUBE_SELECTORS = {

  // ── Search result container ────────────────────────────────────────────────
  // The parent element that wraps all search result items on /results pages.
  // Primary: ytd-video-renderer (standard video cards)
  // Fallback: ytd-search renderer children
  RESULT_CONTAINER: "ytd-item-section-renderer",

  // Each individual video result card
  VIDEO_CARD: "ytd-video-renderer",

  // ── Per-card fields ────────────────────────────────────────────────────────

  // Video title text + href (contains watch?v=VIDEO_ID)
  TITLE_LINK: "a#video-title",

  // Channel name
  CHANNEL_NAME: "ytd-channel-name yt-formatted-string",

  // Description snippet (may be absent on some cards)
  DESCRIPTION: "#description-text",

  // Duration badge (e.g. "12:34")
  DURATION: "span.ytd-thumbnail-overlay-time-status-renderer",

  // View count + publish date live in a single metadata line
  // e.g. "1.2M views  •  3 months ago"
  METADATA_LINE: "#metadata-line span.inline-metadata-item",

  // Thumbnail <img> inside the card
  THUMBNAIL_IMG: "ytd-thumbnail img#img",

  // ── Page-level ─────────────────────────────────────────────────────────────

  // The search query input box (used to read current query)
  SEARCH_INPUT: "input#search",

  // The primary results column where we'll inject the SmartTube panel
  RESULTS_COLUMN: "#primary",

  // ── Injection targets ──────────────────────────────────────────────────────

  // ID we give to the injected "Analyze Videos" button wrapper
  ANALYZE_BTN_ID: "smarttube-analyze-btn",

  // ID of the SmartTube results panel we inject
  PANEL_ID: "smarttube-panel",
};
