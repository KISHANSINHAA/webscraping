# 🎯 AI Prospect Research Agent & Enrichment Portal

A production-grade, highly reliable corporate intelligence and lead enrichment platform. The system validates target domain URLs, runs smart index-page discovery, scraping fallback layers, cleans raw text, parses direct contact information, and generates synthesised value-positioning insights using the Groq API.

Developed with performance, security, and exceptional SaaS dashboard design principles.

---

## 🚀 Key Framework Architecture

- **Smart Link Selection:** Uses `RapidFuzz` string similarity to score and discover up to 5 priority paths (like `/about`, `/contact`, `/solutions`) while automatically ignoring noise paths (`/careers`, `/blog`, `/privacy`).
- **3-Level Scraping Engine:** Employs a robust fallback sequence:
  1. Standard Requests with modern browser header headers.
  2. Alternative rotating mobile/bot User-Agent overrides.
  3. Exponential backoff retry loops.
- **Micro-Data Extraction:** Custom regex patterns and the `phonenumbers` international library format harvested emails, direct lines, and microdata addresses.
- **Context Filtering:** Filters structural noise (`<script>`, `<style>`, Navigation bars, Cookie alerts) and compresses spacing to keep payloads under a tight `< 5000` character limit.
- **Groq LLM Intelligence:** Sends structured text to `llama-3.3-70b-versatile` with low temperature settings, strict anti-hallucination rules, and low-level JSON mode formats.
- **Secure Fail-Safes:** Pydantic validation handles format checks; a secondary corrective retry is attempted upon format error, falling back on database-safe default structures to prevent crashes.

---

## 📂 File Directory

```
webscraping/
├── requirements.txt         # Package dependencies
├── .env                     # Local configuration environment (API Keys - EXCLUDED FROM CODE)
├── .enc                     # Base64-obfuscated secure credentials backup
├── config.py                # Configuration loads and priority keywords
├── database.py              # SQLite table management and company upsert operations
├── scraper.py               # Smart discovery and fallback crawling pipeline
├── agent.py                 # Pydantic schemas and Groq integration routines
├── api.py                   # High-performance FastAPI backend
├── app.py                   # Premium Enterprise Streamlit UI dashboard
├── colab_notebook.py        # Independent single-file execution script for Google Colab
└── AI_Prospect_Research_Agent.ipynb  # Interactive Google Colab Notebook
```

---

## 🛠️ Installation & Setup

We recommend utilizing the ultra-fast rust-based package manager `uv` to establish environment isolation:

### 1. Initialize Virtual Environment
```bash
# Install uv tool globally (if not present)
pip install uv

# Generate localized virtual environment
uv venv

# Activate on Windows:
.venv\Scripts\activate
# Activate on macOS/Linux:
source .venv/bin/activate
```

### 2. Install Project Packages
```bash
uv pip install -r requirements.txt
```

### 3. Set Up Credentials
Create a `.env` file in the root directory (this file is excluded from main codebase files for safety):
```env
GROQ_API_KEY=gsk_your_actual_key_here
DB_NAME=prospects.db
```

---

## 💻 Running the Applications

Both Streamlit and FastAPI applications are designed to run concurrently.

### 1. Streamlit Enterprise Dashboard (Frontend)
Run the professional SaaS analytics and enrichment dashboard:
```bash
uv run streamlit run app.py
```
Open your browser to: **[http://localhost:8501](http://localhost:8501)**

### 2. FastAPI Enrichment Server (Backend)
Launch the microservice API server:
```bash
uv run uvicorn api:app --port 8000
```
- Interactive Swagger API Documentation: **[http://localhost:8000/docs](http://localhost:8000/docs)**
- **POST `/enrich`**: Accepts a URL and returns structured corporate positioning:
  ```json
  { "url": "https://fireflies.ai" }
  ```
- **GET `/results`**: Lists all saved corporate records.

---

## 📓 Google Colab Integration

To execute inside a clean Google Colab runtime:
1. Open Google Colab and upload **`AI_Prospect_Research_Agent.ipynb`**.
2. Run the initialization cell (`!pip install requests beautifulsoup4 rapidfuzz phonenumbers pydantic`).
3. Add your Groq API key to the `API_KEY` configuration.
4. Input target URLs and run the notebook cells to generate `results.json`.
