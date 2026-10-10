/**
 * background.js — SmartTube Background Service Worker (Manifest V3)
 *
 * Listens for messages from content scripts or popup.
 * Proxies ranking requests to the local/remote FastAPI backend server.
 */

const DEFAULT_API_ENDPOINT = "http://127.0.0.1:8000/rank";

chrome.runtime.onInstalled.addListener(() => {
  console.log("[SmartTube] Background Service Worker installed.");
  // Initialize default configuration
  chrome.storage.local.get(["backendUrl", "apiKey"], (items) => {
    if (!items.backendUrl) {
      chrome.storage.local.set({ backendUrl: DEFAULT_API_ENDPOINT });
    }
  });
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "RANK_VIDEOS") {
    handleRankVideos(message.payload)
      .then((data) => sendResponse({ success: true, data }))
      .catch((err) => sendResponse({ success: false, error: err.message }));
    return true; // Keep message channel open for async response
  }

  if (message.type === "CHECK_BACKEND_STATUS") {
    checkHealth()
      .then((status) => sendResponse({ success: true, status }))
      .catch((err) => sendResponse({ success: false, error: err.message }));
    return true;
  }
});

async function getBackendUrl() {
  return new Promise((resolve) => {
    chrome.storage.local.get(["backendUrl"], (items) => {
      resolve(items.backendUrl || DEFAULT_API_ENDPOINT);
    });
  });
}

async function getApiKey() {
  return new Promise((resolve) => {
    chrome.storage.local.get(["apiKey"], (items) => {
      resolve(items.apiKey || null);
    });
  });
}

async function handleRankVideos(payload) {
  const backendUrl = await getBackendUrl();
  const apiKey = await getApiKey();

  const response = await fetch(backendUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      query: payload.query,
      videos: payload.videos,
      api_key: apiKey
    })
  });

  if (!response.ok) {
    let errorDetail = `Backend HTTP error ${response.status}`;
    try {
      const errJson = await response.json();
      if (errJson.detail) errorDetail = errJson.detail;
    } catch (_) {}
    throw new Error(errorDetail);
  }

  return await response.json();
}

async function checkHealth() {
  const backendUrl = await getBackendUrl();
  const rootUrl = backendUrl.replace(/\/rank\/?$/, "/health");
  const resp = await fetch(rootUrl, { method: "GET" });
  if (resp.ok) {
    return await resp.json();
  }
  throw new Error(`Status ${resp.status}`);
}
