// Off-Grid Scout - Enhanced Content Script
// Extracts property listing data from supported UK property websites with multiple fallback selectors

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'extractData') {
    const data = extractPropertyData();
    sendResponse(data);
  }
  return true; // Keep message channel open for async
});

// Utility: get text from first matching selector from array
function getTextFromSelectors(selectors) {
  if (!Array.isArray(selectors)) {
    selectors = [selectors];
  }

  for (const selector of selectors) {
    try {
      const element = document.querySelector(selector);
      if (element && element.textContent && element.textContent.trim()) {
        return element.textContent.trim();
      }
    } catch (e) {
      // Silently continue to next selector
    }
  }
  return null;
}

// Enhanced getText that supports arrays
function getText(selectorOrArray) {
  if (Array.isArray(selectorOrArray)) {
    return getTextFromSelectors(selectorOrArray);
  }
  return getTextFromSelectors([selectorOrArray]);
}

function extractPropertyData() {
  const hostname = window.location.hostname.replace('www.', '');
  console.log(`Off-Grid Scout: Extracting from ${hostname}`);

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
        const result = extractor();
        console.log(`Off-Grid Scout: Successfully extracted from ${domain}`, result);
        return result;
      } catch (e) {
        console.error(`Off-Grid Scout: Extraction failed for ${domain}:`, e);
        return fallbackExtract();
      }
    }
  }

  console.log('Off-Grid Scout: No specific extractor found, using fallback');
  return fallbackExtract();
}

// --- Rightmove --- with multiple fallback selectors
function extractRightmove() {
  const titleSelectors = [
    'h1.property-header-bedroom-and-price',
    'h1.property-header-title',
    'h1[data-testid="header-title"]',
    'h1',
    '.property-header h1',
    '[data-testid="property-header"] h1',
    'title'
  ];

  const addressSelectors = [
    '[data-testid="address-label"]',
    '.property-header-address',
    '.property-header-bedroom-and-price',
    'address',
    '[itemprop="address"]',
    '.property-header h2',
    '.address'
  ];

  const descriptionSelectors = [
    '[data-testid="truncated-text-paragraph"]',
    '.sect-body',
    '.property-description',
    '[data-testid="description"]',
    '.description',
    '#description'
  ];

  const priceSelectors = [
    '[data-testid="price"]',
    '.property-header-price',
    '.price',
    '[itemprop="price"]'
  ];

  const title = getText(titleSelectors) || document.title;
  const address = getText(addressSelectors);
  const description = getText(descriptionSelectors);
  const price = getText(priceSelectors);

  const coords = extractCoordsFromScripts();

  return {
    site: 'Rightmove',
    title,
    address,
    description,
    price,
    url: window.location.href,
    lat: coords.lat,
    lon: coords.lon,
  };
}

// --- Zoopla --- with multiple fallback selectors
function extractZoopla() {
  const titleSelectors = [
    'h1[data-testid="listing-details-title"]',
    'h1.listing-details-title',
    'h1',
    '.listing-details h1',
    'title'
  ];

  const addressSelectors = [
    '[data-testid="listing-details-address"]',
    '.listing-details-address',
    'address',
    '[itemprop="address"]',
    '.address'
  ];

  const descriptionSelectors = [
    '[data-testid="listing-details-description"]',
    '.listing-details-description',
    '.description',
    '#description'
  ];

  const priceSelectors = [
    '[data-testid="listing-details-price"]',
    '.listing-details-price',
    '.price',
    '[itemprop="price"]'
  ];

  const title = getText(titleSelectors) || document.title;
  const address = getText(addressSelectors);
  const description = getText(descriptionSelectors);
  const price = getText(priceSelectors);

  const coords = extractCoordsFromScripts();

  return {
    site: 'Zoopla',
    title,
    address,
    description,
    price,
    url: window.location.href,
    lat: coords.lat,
    lon: coords.lon,
  };
}

// --- OnTheMarket --- (simplified for brevity)
function extractOnTheMarket() {
  const title = getText(['h1.property-detail-title', 'h1', 'title']) || document.title;
  const address = getText(['.property-detail-address', 'address', '.address']);
  const description = getText(['.property-detail-description', '.description', '#description']);
  const price = getText(['.property-detail-price', '.price', '[itemprop="price"]']);

  const coords = extractCoordsFromScripts();

  return {
    site: 'OnTheMarket',
    title,
    address,
    description,
    price,
    url: window.location.href,
    lat: coords.lat,
    lon: coords.lon,
  };
}

// --- Savills --- (simplified for brevity)
function extractSavills() {
  const title = getText(['h1.property-title', 'h1', 'title']) || document.title;
  const address = getText(['.property-address', 'address', '.address']);
  const description = getText(['.property-description', '.description', '#description']);
  const price = getText(['.property-price', '.price', '[itemprop="price"]']);

  const coords = extractCoordsFromScripts();

  return {
    site: 'Savills',
    title,
    address,
    description,
    price,
    url: window.location.href,
    lat: coords.lat,
    lon: coords.lon,
  };
}

// --- PrimeLocation --- (simplified for brevity)
function extractPrimeLocation() {
  const title = getText(['h1.listing-title', 'h1', 'title']) || document.title;
  const address = getText(['.listing-address', 'address', '.address']);
  const description = getText(['.listing-description', '.description', '#description']);
  const price = getText(['.listing-price', '.price', '[itemprop="price"]']);

  const coords = extractCoordsFromScripts();

  return {
    site: 'PrimeLocation',
    title,
    address,
    description,
    price,
    url: window.location.href,
    lat: coords.lat,
    lon: coords.lon,
  };
}

// --- PlotFinder --- (simplified for brevity)
function extractPlotFinder() {
  const title = getText(['h1.plot-title', 'h1', 'title']) || document.title;
  const address = getText(['.plot-address', 'address', '.address']);
  const description = getText(['.plot-description', '.description', '#description']);
  const price = getText(['.plot-price', '.price', '[itemprop="price"]']);

  const coords = extractCoordsFromScripts();

  return {
    site: 'PlotFinder',
    title,
    address,
    description,
    price,
    url: window.location.href,
    lat: coords.lat,
    lon: coords.lon,
  };
}

// Enhanced coordinate extraction with multiple methods
function extractCoordsFromScripts() {
  let lat = null, lon = null;

  // Method 1: Meta tags (Open Graph, Schema.org)
  const latMeta = document.querySelector('meta[property="place:location:latitude"], meta[name="latitude"], meta[property="latitude"]');
  const lonMeta = document.querySelector('meta[property="place:location:longitude"], meta[name="longitude"], meta[property="longitude"]');
  if (latMeta && lonMeta) {
    lat = parseFloat(latMeta.getAttribute('content'));
    lon = parseFloat(lonMeta.getAttribute('content'));
    if (!isNaN(lat) && !isNaN(lon) && isUKCoord(lat, lon)) {
      console.log('Off-Grid Scout: Found coordinates in meta tags');
      return { lat, lon };
    }
  }

  // Method 2: Search through script tags for coordinate patterns
  const scripts = document.querySelectorAll('script');
  for (const script of scripts) {
    const text = script.textContent || script.innerHTML || '';

    // Pattern: latitude: 51.123, longitude: -0.456
    const latMatch = text.match(/["']?latitude["']?\s*[=:]\s*(-?\d+\.\d+)/i);
    const lonMatch = text.match(/["']?longitude["']?\s*[=:]\s*(-?\d+\.\d+)/i);
    if (latMatch && lonMatch) {
      lat = parseFloat(latMatch[1]);
      lon = parseFloat(lonMatch[1]);
      if (isUKCoord(lat, lon)) {
        console.log('Off-Grid Scout: Found coordinates in script (latitude/longitude pattern)');
        return { lat, lon };
      }
    }

    // Pattern: "lat":51.123,"lng":-0.456
    const latLngMatch = text.match(/["']lat["']\s*:\s*(-?\d+\.\d+).*?["']l(?:ng|on)["']\s*:\s*(-?\d+\.\d+)/i);
    if (latLngMatch) {
      lat = parseFloat(latLngMatch[1]);
      lon = parseFloat(latLngMatch[2]);
      if (isUKCoord(lat, lon)) {
        console.log('Off-Grid Scout: Found coordinates in script (lat/lng pattern)');
        return { lat, lon };
      }
    }

    // Pattern: Google Maps center: [51.123, -0.456]
    const centerMatch = text.match(/center\s*[:=]\s*\[\s*(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)\s*\]/);
    if (centerMatch) {
      lat = parseFloat(centerMatch[1]);
      lon = parseFloat(centerMatch[2]);
      if (isUKCoord(lat, lon)) {
        console.log('Off-Grid Scout: Found coordinates in script (Google Maps center)');
        return { lat, lon };
      }
    }

    // Pattern: Leaflet map center
    const leafletMatch = text.match(/setView\s*\(\s*\[\s*(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)\s*\]/);
    if (leafletMatch) {
      lat = parseFloat(leafletMatch[1]);
      lon = parseFloat(leafletMatch[2]);
      if (isUKCoord(lat, lon)) {
        console.log('Off-Grid Scout: Found coordinates in script (Leaflet setView)');
        return { lat, lon };
      }
    }
  }

  // Method 3: Data attributes on map elements
  const mapEl = document.querySelector('[data-lat][data-lng], [data-latitude][data-longitude], [data-coordinates]');
  if (mapEl) {
    lat = parseFloat(mapEl.getAttribute('data-lat') || mapEl.getAttribute('data-latitude'));
    lon = parseFloat(mapEl.getAttribute('data-lng') || mapEl.getAttribute('data-longitude'));

    // Try parsing data-coordinates attribute
    if (isNaN(lat) || isNaN(lon)) {
      const coordsAttr = mapEl.getAttribute('data-coordinates');
      if (coordsAttr) {
        const coordsMatch = coordsAttr.match(/(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)/);
        if (coordsMatch) {
          lat = parseFloat(coordsMatch[1]);
          lon = parseFloat(coordsMatch[2]);
        }
      }
    }

    if (isUKCoord(lat, lon)) {
      console.log('Off-Grid Scout: Found coordinates in data attributes');
      return { lat, lon };
    }
  }

  // Method 4: Iframe src with coordinates
  const iframes = document.querySelectorAll('iframe[src*="maps"], iframe[src*="google"], iframe[src*="leaflet"]');
  for (const iframe of iframes) {
    const src = iframe.getAttribute('src') || '';
    // Look for q= or ll= parameters in Google Maps URLs
    const qMatch = src.match(/[?&]q=(-?\d+\.\d+),(-?\d+\.\d+)/);
    const llMatch = src.match(/[?&]ll=(-?\d+\.\d+),(-?\d+\.\d+)/);

    if (qMatch) {
      lat = parseFloat(qMatch[1]);
      lon = parseFloat(qMatch[2]);
    } else if (llMatch) {
      lat = parseFloat(llMatch[1]);
      lon = parseFloat(llMatch[2]);
    }

    if (isUKCoord(lat, lon)) {
      console.log('Off-Grid Scout: Found coordinates in iframe src');
      return { lat, lon };
    }
  }

  console.log('Off-Grid Scout: No coordinates found');
  return { lat: null, lon: null };
}

function fallbackExtract() {
  console.log('Off-Grid Scout: Using fallback extraction');

  // Try to get any h1 as title
  const h1 = document.querySelector('h1');
  const title = h1 ? h1.textContent.trim() : document.title;

  // Try to get address from common elements
  const addressEl = document.querySelector('address, [itemprop="address"], .address');
  const address = addressEl ? addressEl.textContent.trim() : null;

  // Try to get description
  const descEl = document.querySelector('meta[name="description"], .description, #description');
  let description = null;
  if (descEl) {
    description = descEl.getAttribute('content') || descEl.textContent.trim();
  }

  const coords = extractCoordsFromScripts();

  return {
    site: 'Unknown',
    title,
    address,
    description,
    price: null,
    url: window.location.href,
    lat: coords.lat,
    lon: coords.lon,
  };
}

function isUKCoord(lat, lon) {
  return !isNaN(lat) && !isNaN(lon) && lat >= 49 && lat <= 61 && lon >= -8 && lon <= 2;
}
