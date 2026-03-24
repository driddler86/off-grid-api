// Off-Grid Scout - Background Service Worker
// Handles extension lifecycle events and badge updates

const API_BASE = 'https://www.offgridscout.co.uk';

// Supported domains for badge indicator
const SUPPORTED_DOMAINS = [
  'rightmove.co.uk',
  'zoopla.co.uk',
  'onthemarket.com',
  'savills.com',
  'primelocation.com',
  'plotfinder.net',
];

// Update badge when tab changes
chrome.tabs.onActivated.addListener(async (activeInfo) => {
  try {
    const tab = await chrome.tabs.get(activeInfo.tabId);
    updateBadge(tab);
  } catch (e) { /* tab may not exist */ }
});

// Update badge when URL changes
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.url || changeInfo.status === 'complete') {
    updateBadge(tab);
  }
});

function updateBadge(tab) {
  if (!tab.url) {
    chrome.action.setBadgeText({ tabId: tab.id, text: '' });
    return;
  }

  try {
    const url = new URL(tab.url);
    const hostname = url.hostname.replace('www.', '');
    const isSupported = SUPPORTED_DOMAINS.some(d => hostname.includes(d));

    if (isSupported) {
      chrome.action.setBadgeText({ tabId: tab.id, text: 'GO' });
      chrome.action.setBadgeBackgroundColor({ tabId: tab.id, color: '#10b981' });
    } else {
      chrome.action.setBadgeText({ tabId: tab.id, text: '' });
    }
  } catch (e) {
    chrome.action.setBadgeText({ tabId: tab.id, text: '' });
  }
}

// Listen for install/update
chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === 'install') {
    // Open welcome/setup page on first install
    chrome.tabs.create({ url: `${API_BASE}/#pricing` });
  }
});

console.log('Off-Grid Scout background service worker loaded');
