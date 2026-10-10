/**
 * popup.js — Settings controller for SmartTube popup UI
 */

document.addEventListener("DOMContentLoaded", () => {
  const backendUrlInput = document.getElementById("backendUrl");
  const apiKeyInput = document.getElementById("apiKey");
  const saveBtn = document.getElementById("saveBtn");
  const statusDot = document.getElementById("statusDot");
  const statusText = document.getElementById("statusText");
  const toast = document.getElementById("toast");

  // Load saved preferences
  chrome.storage.local.get(["backendUrl", "apiKey"], (items) => {
    if (items.backendUrl) {
      backendUrlInput.value = items.backendUrl;
    } else {
      backendUrlInput.value = "http://127.0.0.1:8000/rank";
    }

    if (items.apiKey) {
      apiKeyInput.value = items.apiKey;
    }

    checkBackendHealth();
  });

  saveBtn.addEventListener("click", () => {
    const backendUrl = backendUrlInput.value.trim() || "http://127.0.0.1:8000/rank";
    const apiKey = apiKeyInput.value.trim();

    chrome.storage.local.set({ backendUrl, apiKey }, () => {
      showToast("Settings saved successfully!");
      checkBackendHealth();
    });
  });

  async function checkBackendHealth() {
    statusDot.className = "dot";
    statusText.textContent = "Checking...";

    try {
      const response = await chrome.runtime.sendMessage({ type: "CHECK_BACKEND_STATUS" });
      if (response && response.success) {
        statusDot.className = "dot connected";
        statusText.textContent = "Connected (v" + (response.status?.version || "1.0") + ")";
      } else {
        throw new Error(response ? response.error : "Offline");
      }
    } catch (err) {
      statusDot.className = "dot disconnected";
      statusText.textContent = "Offline / Error";
    }
  }

  function showToast(msg) {
    toast.textContent = msg;
    toast.className = "toast success";
    setTimeout(() => {
      toast.style.display = "none";
    }, 2500);
  }
});
