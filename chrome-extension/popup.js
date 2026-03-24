// Off-Grid Scout - Popup Logic
const API_BASE = 'https://www.offgridscout.co.uk';

// DOM Elements
const setupScreen = document.getElementById('setup-screen');
const mainScreen = document.getElementById('main-screen');
const tierBadge = document.getElementById('tier-badge');
const apiKeyInput = document.getElementById('api-key-input');
const saveKeyBtn = document.getElementById('save-key-btn');
const registerLink = document.getElementById('register-link');
const registerForm = document.getElementById('register-form');
const registerEmail = document.getElementById('register-email');
const registerBtn = document.getElementById('register-btn');
const setupMsg = document.getElementById('setup-msg');
const scansCount = document.getElementById('scans-count');
const progressFill = document.getElementById('progress-fill');
const siteDot = document.getElementById('site-dot');
const siteName = document.getElementById('site-name');
const siteUrl = document.getElementById('site-url');
const scanBtn = document.getElementById('scan-btn');
const loadingSection = document.getElementById('loading-section');
const resultsSection = document.getElementById('results-section');
const scoreValue = document.getElementById('score-value');
const scoreVerdict = document.getElementById('score-verdict');
const copyBtn = document.getElementById('copy-btn');
const emailBtn = document.getElementById('email-btn');
const upgradeBanner = document.getElementById('upgrade-banner');
const logoutBtn = document.getElementById('logout-btn');

// Supported property sites
const SUPPORTED_SITES = {
  'rightmove.co.uk': 'Rightmove',
  'zoopla.co.uk': 'Zoopla',
  'onthemarket.com': 'OnTheMarket',
  'savills.com': 'Savills',
  'primelocation.com': 'PrimeLocation',
  'plotfinder.net': 'PlotFinder',
};

let currentApiKey = null;
let currentTab = null;
let lastDossier = null;

// --- Initialization ---
async function init() {
  const stored = await chrome.storage.local.get(['apiKey']);
  if (stored.apiKey) {
    currentApiKey = stored.apiKey;
    await showMainScreen();
  } else {
    showSetupScreen();
  }
}

function showSetupScreen() {
  setupScreen.classList.remove('hidden');
  mainScreen.classList.add('hidden');
}

async function showMainScreen() {
  setupScreen.classList.add('hidden');
  mainScreen.classList.remove('hidden');
  await loadAccountInfo();
  await checkCurrentTab();
}

// --- Account Management ---
async function loadAccountInfo() {
  try {
    const res = await fetch(`${API_BASE}/auth/verify`, {
      headers: { 'X-API-Key': currentApiKey }
    });
    if (!res.ok) throw new Error('Invalid key');
    const data = await res.json();

    // Update tier badge
    const tier = data.tier || 'free';
    tierBadge.textContent = tier.toUpperCase();
    tierBadge.className = `tier-badge tier-${tier}`;

    // Update scan count
    const used = data.scans_today || 0;
    const limit = data.daily_limit || 3;
    scansCount.textContent = `${used} / ${limit}`;
    progressFill.style.width = `${Math.min(100, (used / limit) * 100)}%`;

    // Show upgrade banner for free users
    if (tier === 'free') {
      upgradeBanner.classList.remove('hidden');
    } else {
      upgradeBanner.classList.add('hidden');
    }
  } catch (e) {
    console.error('Failed to load account:', e);
    // Key might be invalid
    showMsg(setupMsg, 'API key appears invalid. Please re-enter.', 'error');
    await chrome.storage.local.remove(['apiKey']);
    currentApiKey = null;
    showSetupScreen();
  }
}

// --- Tab Detection ---
async function checkCurrentTab() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    currentTab = tab;
    const url = new URL(tab.url);
    const hostname = url.hostname.replace('www.', '');

    let supported = false;
    for (const [domain, name] of Object.entries(SUPPORTED_SITES)) {
      if (hostname.includes(domain)) {
        siteName.textContent = name;
        siteDot.classList.add('supported');
        siteDot.classList.remove('unsupported');
        supported = true;
        break;
      }
    }

    if (!supported) {
      siteName.textContent = 'Unsupported site';
      siteDot.classList.add('unsupported');
      siteDot.classList.remove('supported');
    }

    siteUrl.textContent = tab.url.substring(0, 60) + (tab.url.length > 60 ? '...' : '');
    scanBtn.disabled = !supported;

  } catch (e) {
    siteName.textContent = 'Cannot detect page';
    siteDot.classList.add('unsupported');
    scanBtn.disabled = true;
  }
}

// --- Scanning ---
async function scanProperty() {
  scanBtn.disabled = true;
  loadingSection.classList.remove('hidden');
  resultsSection.classList.add('hidden');

  try {
    // Extract data from current page via content script
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const pageData = await chrome.tabs.sendMessage(tab.id, { action: 'extractData' });

    if (!pageData || !pageData.title) {
      throw new Error('Could not extract property data from this page');
    }

    // Call the API
    const res = await fetch(`${API_BASE}/scan`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': currentApiKey,
      },
      body: JSON.stringify({
        url: tab.url,
        title: pageData.title,
        lat: pageData.lat || null,
        lon: pageData.lon || null,
        description: pageData.description || null,
      }),
    });

    if (res.status === 429) {
      throw new Error('Daily scan limit reached. Upgrade for more scans!');
    }
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Scan failed');
    }

    const result = await res.json();
    lastDossier = result.dossier;
    displayResults(result);
    await loadAccountInfo(); // Refresh scan count

  } catch (e) {
    loadingSection.classList.add('hidden');
    showMsg(setupMsg, e.message, 'error');
  }

  scanBtn.disabled = false;
}

// --- Display Results ---
function displayResults(result) {
  loadingSection.classList.add('hidden');
  resultsSection.classList.remove('hidden');

  const dossier = result.dossier || '';

  // Extract score from dossier text
  const scoreMatch = dossier.match(/(?:sovereignty|overall|total).*?(\d{1,3})(?:\/100|%)/i);
  const score = scoreMatch ? parseInt(scoreMatch[1]) : null;

  if (score !== null) {
    scoreValue.textContent = score;
    scoreValue.className = 'score-value ' + (score >= 70 ? 'score-high' : score >= 40 ? 'score-mid' : 'score-low');
    scoreVerdict.textContent = score >= 70 ? 'Excellent Potential' : score >= 40 ? 'Moderate Potential' : 'Challenging Site';
  } else {
    scoreValue.textContent = 'N/A';
    scoreValue.className = 'score-value';
    scoreVerdict.textContent = 'See full report below';
  }

  // Extract category scores from dossier
  const extractField = (patterns) => {
    for (const p of patterns) {
      const m = dossier.match(p);
      if (m) return m[1].substring(0, 15);
    }
    return '--';
  };

  document.getElementById('res-energy').textContent = extractField([/energy[:\s]+([^\n]+)/i, /solar[:\s]+([^\n]+)/i]);
  document.getElementById('res-water').textContent = extractField([/water[:\s]+([^\n]+)/i, /borehole[:\s]+([^\n]+)/i]);
  document.getElementById('res-flood').textContent = extractField([/flood[:\s]+([^\n]+)/i]);
  document.getElementById('res-planning').textContent = extractField([/planning[:\s]+([^\n]+)/i, /permitted[:\s]+([^\n]+)/i]);
  document.getElementById('res-grid').textContent = extractField([/grid[:\s]+([^\n]+)/i, /electric[:\s]+([^\n]+)/i]);
  document.getElementById('res-solar').textContent = extractField([/solar.*?(\d[^\n]*)/i, /irradiance[:\s]+([^\n]+)/i]);

  // Feature gating
  const features = result.features || {};
  emailBtn.disabled = !features.email_dossier;
  if (!features.email_dossier) {
    emailBtn.title = 'Upgrade to Scout to email reports';
  }
}

// --- Actions ---
copyBtn.addEventListener('click', async () => {
  if (lastDossier) {
    await navigator.clipboard.writeText(lastDossier);
    copyBtn.textContent = '\u2705 Copied!';
    setTimeout(() => { copyBtn.innerHTML = '&#x1f4cb; Copy Report'; }, 2000);
  }
});

emailBtn.addEventListener('click', async () => {
  if (!lastDossier) return;
  const email = prompt('Enter email address for the report:');
  if (!email) return;

  try {
    const res = await fetch(`${API_BASE}/email`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-API-Key': currentApiKey },
      body: JSON.stringify({ email, dossier: lastDossier }),
    });
    if (res.ok) {
      emailBtn.textContent = '\u2705 Sent!';
      setTimeout(() => { emailBtn.innerHTML = '&#x1f4e7; Email Report'; }, 2000);
    }
  } catch (e) {
    alert('Failed to send email: ' + e.message);
  }
});

upgradeBanner.addEventListener('click', () => {
  chrome.tabs.create({ url: `${API_BASE}/#pricing` });
});

// --- API Key Management ---
saveKeyBtn.addEventListener('click', async () => {
  const key = apiKeyInput.value.trim();
  if (!key.startsWith('ogs_')) {
    showMsg(setupMsg, 'Invalid key format. Keys start with ogs_', 'error');
    return;
  }
  currentApiKey = key;
  await chrome.storage.local.set({ apiKey: key });
  await showMainScreen();
});

registerLink.addEventListener('click', (e) => {
  e.preventDefault();
  registerForm.classList.toggle('hidden');
});

registerBtn.addEventListener('click', async () => {
  const email = registerEmail.value.trim();
  if (!email || !email.includes('@')) {
    showMsg(setupMsg, 'Please enter a valid email', 'error');
    return;
  }

  registerBtn.disabled = true;
  registerBtn.textContent = 'Registering...';

  try {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });

    if (!res.ok) throw new Error('Registration failed');
    const data = await res.json();

    // Auto-save the key
    currentApiKey = data.api_key;
    await chrome.storage.local.set({ apiKey: data.api_key });

    showMsg(setupMsg, `Account created! Key: ${data.api_key.substring(0, 20)}...`, 'success');
    setTimeout(() => showMainScreen(), 1500);

  } catch (e) {
    showMsg(setupMsg, 'Registration failed: ' + e.message, 'error');
  }

  registerBtn.disabled = false;
  registerBtn.textContent = 'Register';
});

logoutBtn.addEventListener('click', async () => {
  await chrome.storage.local.remove(['apiKey']);
  currentApiKey = null;
  apiKeyInput.value = '';
  showSetupScreen();
});

scanBtn.addEventListener('click', scanProperty);

// --- Helpers ---
function showMsg(container, text, type) {
  container.innerHTML = `<div class="msg msg-${type}">${text}</div>`;
  setTimeout(() => { container.innerHTML = ''; }, 5000);
}

// --- Start ---
init();
