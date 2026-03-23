// Off-Grid Scout - Content Script
// Extracts property listing data from supported UK property websites

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'extractData') {
    const data = extractPropertyData();
    sendResponse(data);
  }
  return true; // Keep message channel open for async
});

function extractPropertyData() {
  const hostname = window.location.hostname.replace('www.', '');

  const extractors = {
    'rightmove.co.uk': extractRightmove,
    'zoopla.co.uk': extractZoopla,
    'onthemarket.com': extractOnTheMarket,
    'savills.com': extractSavills,
    'primelocation.com': extractPrimeLocation,
    'plotfinder.net': extractPlotFinder,
  };

  for (const [domain, extractor] of Object.entries(extractors)) {
    if (hostname.includes(domain)) {
      try {
        return extractor();
      } catch (e) {
        console.error(`Off-Grid Scout: Extraction failed for ${domain}:`, e);
        return fallbackExtract();
      }
    }
  }

  return fallbackExtract();
}

// --- Rightmove ---
function extractRightmove() {
  const title = getText('h1.property-header-bedroom-and-price') ||
                getText('h1') ||
                document.title;

  const address = getText('[data-testid="address-label"]') ||
                  getText('.property-header-bedroom-and-price') ||
                  getText('address');

  const description = getText('[data-testid="truncated-text-paragraph"]') ||
                      getText('.sect-body') ||
                      getMetaContent('description');

  // Try to get coordinates from page scripts
  const coords = extractCoordsFromScripts();

  return {
    title: cleanText(`${title} ${address}`.trim()),
    description: cleanText(description),
    lat: coords.lat,
    lon: coords.lon,
    url: window.location.href,
    source: 'rightmove',
  };
}

// --- Zoopla ---
function extractZoopla() {
  const title = getText('h1[data-testid="listing-title"]') ||
                getText('h1') ||
                document.title;

  const address = getText('[data-testid="address-label"]') ||
                  getText('h2.listing-details-address');

  const description = getText('[data-testid="listing_description"]') ||
                      getText('.listing-details-tab') ||
                      getMetaContent('description');

  const coords = extractCoordsFromScripts();

  return {
    title: cleanText(`${title} ${address || ''}`.trim()),
    description: cleanText(description),
    lat: coords.lat,
    lon: coords.lon,
    url: window.location.href,
    source: 'zoopla',
  };
}

// --- OnTheMarket ---
function extractOnTheMarket() {
  const title = getText('h1.title') ||
                getText('h1') ||
                document.title;

  const description = getText('.description') ||
                      getText('.property-description') ||
                      getMetaContent('description');

  const coords = extractCoordsFromScripts();

  return {
    title: cleanText(title),
    description: cleanText(description),
    lat: coords.lat,
    lon: coords.lon,
    url: window.location.href,
    source: 'onthemarket',
  };
}

// --- Savills ---
function extractSavills() {
  const title = getText('.property-detail__title') ||
                getText('h1') ||
                document.title;

  const description = getText('.property-detail__description') ||
                      getMetaContent('description');

  const coords = extractCoordsFromScripts();

  return {
    title: cleanText(title),
    description: cleanText(description),
    lat: coords.lat,
    lon: coords.lon,
    url: window.location.href,
    source: 'savills',
  };
}

// --- PrimeLocation ---
function extractPrimeLocation() {
  const title = getText('h1') || document.title;
  const description = getText('.listing-description') ||
                      getMetaContent('description');

  const coords = extractCoordsFromScripts();

  return {
    title: cleanText(title),
    description: cleanText(description),
    lat: coords.lat,
    lon: coords.lon,
    url: window.location.href,
    source: 'primelocation',
  };
}

// --- PlotFinder ---
function extractPlotFinder() {
  const title = getText('h1') || document.title;
  const description = getText('.plot-description') ||
                      getText('.description') ||
                      getMetaContent('description');

  const coords = extractCoordsFromScripts();

  return {
    title: cleanText(title),
    description: cleanText(description),
    lat: coords.lat,
    lon: coords.lon,
    url: window.location.href,
    source: 'plotfinder',
  };
}

// --- Fallback ---
function fallbackExtract() {
  return {
    title: cleanText(document.title),
    description: cleanText(getMetaContent('description') || ''),
    lat: null,
    lon: null,
    url: window.location.href,
    source: 'unknown',
  };
}

// --- Utilities ---
function getText(selector) {
  const el = document.querySelector(selector);
  return el ? el.textContent.trim() : '';
}

function getMetaContent(name) {
  const meta = document.querySelector(`meta[name="${name}"]`) ||
               document.querySelector(`meta[property="og:${name}"]`);
  return meta ? meta.getAttribute('content') : '';
}

function cleanText(text) {
  if (!text) return '';
  return text.replace(/\s+/g, ' ').trim().substring(0, 5000);
}

function extractCoordsFromScripts() {
  // Try to find lat/lon in page scripts or data attributes
  let lat = null, lon = null;

  // Method 1: Check meta tags
  const latMeta = document.querySelector('meta[property="place:location:latitude"]');
  const lonMeta = document.querySelector('meta[property="place:location:longitude"]');
  if (latMeta && lonMeta) {
    lat = parseFloat(latMeta.getAttribute('content'));
    lon = parseFloat(lonMeta.getAttribute('content'));
    if (!isNaN(lat) && !isNaN(lon)) return { lat, lon };
  }

  // Method 2: Search through script tags for coordinate patterns
  const scripts = document.querySelectorAll('script:not([src])');
  for (const script of scripts) {
    const text = script.textContent;

    // Pattern: latitude: 51.123, longitude: -0.456
    const latMatch = text.match(/["']?latitude["']?\s*[=:]\s*(-?\d+\.\d+)/i);
    const lonMatch = text.match(/["']?longitude["']?\s*[=:]\s*(-?\d+\.\d+)/i);
    if (latMatch && lonMatch) {
      lat = parseFloat(latMatch[1]);
      lon = parseFloat(lonMatch[1]);
      if (isUKCoord(lat, lon)) return { lat, lon };
    }

    // Pattern: "lat":51.123,"lng":-0.456
    const latLngMatch = text.match(/["']lat["']\s*:\s*(-?\d+\.\d+).*?["']l(?:ng|on)["']\s*:\s*(-?\d+\.\d+)/i);
    if (latLngMatch) {
      lat = parseFloat(latLngMatch[1]);
      lon = parseFloat(latLngMatch[2]);
      if (isUKCoord(lat, lon)) return { lat, lon };
    }

    // Pattern: center: [51.123, -0.456]
    const centerMatch = text.match(/center\s*:\s*\[\s*(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)\s*\]/i);
    if (centerMatch) {
      lat = parseFloat(centerMatch[1]);
      lon = parseFloat(centerMatch[2]);
      if (isUKCoord(lat, lon)) return { lat, lon };
    }
  }

  // Method 3: Check data attributes on map elements
  const mapEl = document.querySelector('[data-lat][data-lng]') ||
                document.querySelector('[data-latitude][data-longitude]');
  if (mapEl) {
    lat = parseFloat(mapEl.getAttribute('data-lat') || mapEl.getAttribute('data-latitude'));
    lon = parseFloat(mapEl.getAttribute('data-lng') || mapEl.getAttribute('data-longitude'));
    if (isUKCoord(lat, lon)) return { lat, lon };
  }

  return { lat: null, lon: null };
}

function isUKCoord(lat, lon) {
  return !isNaN(lat) && !isNaN(lon) && lat >= 49 && lat <= 61 && lon >= -8 && lon <= 2;
}

console.log('Off-Grid Scout content script loaded');
