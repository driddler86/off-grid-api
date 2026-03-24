# 🏕️ Off-Grid Scout API

**Autonomous property evaluation engine for off-grid living in the UK.**

Off-Grid Scout analyzes UK land plots across multiple dimensions — planning policy, environmental risk, energy potential, water resources, and terrain — to generate a comprehensive "Sovereignty Score" that rates a property's suitability for off-grid development.

## 🏗️ Architecture

The system operates in two phases:

### Phase 1: Discovery Engine (Filtering)
- **ListingHunter** — Analyzes property listing text for green/red flags using regex pattern matching
- **StressHunter** — Checks flood risk (UK Environment Agency) and grid proximity (OpenStreetMap)
- **HistoryHunter** — Searches for "Ghost" planning applications (refused residential apps = Paragraph 84 opportunity)

### Phase 2: Evaluation Engine (Sovereignty Score)
- **OSLandRover** — Terrain analysis (elevation, slope, aspect) and road access check
- **EnergyHunter** — Solar irradiance & wind speed from NASA POWER + Open-Meteo
- **ResourceHunter** — Aquifer productivity & soil data from BGS
- **PolicyHunter** — PDF policy document keyword analysis (Class Q, Para 84, brownfield)

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Docker (optional)

### Local Development

```bash
# Clone the repository
git clone https://github.com/driddler86/off-grid-api.git
cd off-grid-api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run the API server
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

### Docker

```bash
docker build -t off-grid-scout .
docker run -p 8000:8000 off-grid-scout
```

### Streamlit Dashboard

```bash
streamlit run app.py
```

## 📡 API Endpoints

### `GET /health`
Health check endpoint.

### `POST /scan`
Scan a property listing and generate a dossier.

**Request Body:**
```json
{
  "url": "https://example.com/listing/12345",
  "title": "5 Acres Amenity Land, Cornwall",
  "lat": 50.2660,
  "lon": -5.0527,
  "description": "Beautiful off-grid amenity land with spring water."
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string | ✅ | Listing URL |
| `title` | string | ✅ | Listing title |
| `lat` | float | ❌ | Latitude (geocoded from title if missing) |
| `lon` | float | ❌ | Longitude (geocoded from title if missing) |
| `description` | string | ❌ | Listing description text |

**Response:**
```json
{
  "status": "success",
  "dossier": "... full formatted dossier text ..."
}
```

### `POST /email`
Email a dossier to a recipient.

**Request Body:**
```json
{
  "email": "user@example.com",
  "dossier": "... dossier content ..."
}
```

## ⚙️ Configuration

Configuration is managed via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `ALLOWED_ORIGINS` | `*` | Comma-separated CORS origins |
| `SMTP_HOST` | — | SMTP server hostname |
| `SMTP_PORT` | `587` | SMTP server port |
| `SMTP_USER` | — | SMTP username |
| `SMTP_PASS` | — | SMTP password |
| `FROM_EMAIL` | `SMTP_USER` | Sender email address |

Create a `.env` file in the project root:

```env
ALLOWED_ORIGINS=chrome-extension://your-extension-id,http://localhost:3000
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
FROM_EMAIL=noreply@offgridscout.co.uk
```

## 🌐 Data Sources

| Source | Data | Module |
|--------|------|--------|
| [UK Environment Agency](https://environment.data.gov.uk/) | Flood risk zones | `stress_hunter.py` |
| [OpenStreetMap Overpass](https://overpass-api.de/) | Power grid proximity, roads | `stress_hunter.py`, `os_land_rover.py` |
| [NASA POWER](https://power.larc.nasa.gov/) | Solar irradiance, wind speed | `energy_hunter.py` |
| [Open-Meteo](https://open-meteo.com/) | Historical weather data | `energy_hunter.py` |
| [British Geological Survey](https://www.bgs.ac.uk/) | Aquifer, soil data | `resource_hunter.py` |
| [PlanIt API](https://www.planit.org.uk/) | Planning application history | `history_hunter.py` |
| [OpenTopoData](https://www.opentopodata.org/) | Elevation, terrain | `os_land_rover.py` |
| [Nominatim](https://nominatim.openstreetmap.org/) | Geocoding (title → coords) | `api.py` |

## 📊 Scoring System

### Sovereignty Score (0-100)
Weighted combination of three factors:
- **Planning & Policy (40%)** — Keywords found in planning documents
- **Energy Potential (30%)** — Solar irradiance + wind speed (terrain-adjusted)
- **Water & Resources (30%)** — Aquifer productivity + soil quality

**Modifiers:**
- 🚫 **-50%** if no road access within 150m
- 👻 **+20%** if Ghost Application found (Paragraph 84 boost)

### Discovery Verdict
- ❌ **NO-GO** — Failed critical checks (flood zone 3 or developer trap)
- 🌟 **PRIME PARAGRAPH 84 CANDIDATE** — Ghost application found
- ✅ **STRONG OFF-GRID POTENTIAL** — Score > 50
- ⚠️ **MARGINAL** — Requires manual review

## 🔧 Deployment on Render

1. Push to GitHub
2. Create a new **Web Service** on [Render](https://render.com)
3. Connect your GitHub repo
4. Set:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn api:app --host 0.0.0.0 --port 8000`
5. Add environment variables in Render dashboard

## 📁 Project Structure

```
off-grid-api/
├── api.py                 # FastAPI REST endpoints
├── app.py                 # Streamlit dashboard
├── unified_scout.py       # Grand Unification Engine (orchestrator)
├── live_scanner.py        # Dossier generator
├── autonomous_scout.py    # Phase 1: Discovery Engine
├── master_scout.py        # Phase 2: Evaluation Engine
├── scoring.py             # Sovereignty Score calculator
├── listing_hunter.py      # Listing text analysis
├── stress_hunter.py       # Flood risk & grid distance
├── history_hunter.py      # Planning history (Ghost apps)
├── energy_hunter.py       # Solar & wind data
├── resource_hunter.py     # Aquifer & soil data
├── os_land_rover.py       # Terrain & access analysis
├── policy_hunter.py       # Planning policy PDF analysis
├── requirements.txt       # Python dependencies
├── Dockerfile             # Docker container config
└── README.md              # This file
```

## 📄 License

MIT License

## 👤 Author

**driddler86** — [GitHub](https://github.com/driddler86)
