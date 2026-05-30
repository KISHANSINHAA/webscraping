# ================================
# 🏆 Hackathon Template Notebook
# Prospect Research Agent
# ================================

# Note: Before running in Google Colab, make sure to install dependencies:
# !pip install requests beautifulsoup4 rapidfuzz phonenumbers pydantic

import os
import re
import json
import time
import urllib.parse
import requests
from bs4 import BeautifulSoup
import phonenumbers
from rapidfuzz import fuzz
from pydantic import BaseModel, Field
from typing import List, Dict, Set, Any, Tuple

# ========= CONFIG =========
# 🔑 Add your API key here or load it from the environment variables
API_KEY = os.getenv("GROQ_API_KEY")

# ----------------- CONSTANTS & HELPERS -----------------
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

TIMEOUT = 10
MAX_DISCOVERED_PAGES = 5

PRIORITY_KEYWORDS = ["about", "about-us", "company", "services", "solutions", "products", "contact", "contact-us", "who-we-are", "industries"]
IGNORE_KEYWORDS = ["blog", "careers", "privacy", "terms", "news", "events"]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0"
]

# ----------------- PYDANTIC SCHEMA -----------------
class CompanyProfile(BaseModel):
    website_name: str = Field(default="")
    company_name: str = Field(default="")
    address: str = Field(default="")
    mobile_number: str = Field(default="")
    mail: List[str] = Field(default_factory=list)
    core_service: str = Field(default="")
    target_customer: str = Field(default="")
    probable_pain_point: str = Field(default="")
    outreach_opener: str = Field(default="")

# ----------------- INTERNAL SCRAPING FUNCTIONS -----------------
def _normalize_url(url: str) -> str:
    url = url.strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    parsed = urllib.parse.urlparse(url)
    if not parsed.netloc:
        return ""
    return url

def _get_base_domain(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    domain = parsed.netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain

def _extract_links(html: str, base_url: str) -> Set[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = set()
    base_domain = _get_base_domain(base_url)
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        absolute_url = urllib.parse.urljoin(base_url, href)
        parsed_abs = urllib.parse.urlparse(absolute_url)
        abs_domain = parsed_abs.netloc.lower().replace("www.", "")
        if abs_domain == base_domain or abs_domain.endswith("." + base_domain):
            cleaned = urllib.parse.urlunparse((parsed_abs.scheme, parsed_abs.netloc, parsed_abs.path, parsed_abs.params, "", ""))
            links.add(cleaned)
    return links

def _score_links(links: Set[str], base_url: str) -> List[str]:
    scored = []
    for link in links:
        parsed = urllib.parse.urlparse(link)
        path = parsed.path.lower().strip("/")
        if not path:
            continue
        if any(ignore in path for ignore in IGNORE_KEYWORDS):
            continue
        path_seg = path.replace("-", " ").replace("_", " ")
        max_score = 0
        for priority in PRIORITY_KEYWORDS:
            score = max(fuzz.ratio(priority, path_seg), fuzz.partial_ratio(priority, path_seg))
            if score > max_score:
                max_score = score
        if max_score > 50 or any(priority in path for priority in PRIORITY_KEYWORDS):
            boost = 30 if any(priority in path for priority in PRIORITY_KEYWORDS) else 0
            scored.append((link, max_score + boost))
    scored.sort(key=lambda x: x[1], reverse=True)
    selected = [base_url]
    for link, _ in scored:
        if link not in selected:
            selected.append(link)
            if len(selected) >= MAX_DISCOVERED_PAGES:
                break
    return selected

def _scrape(url: str) -> str:
    # Method 1
    try:
        res = requests.get(url, headers={"User-Agent": USER_AGENTS[0]}, timeout=TIMEOUT)
        if res.status_code == 200:
            return res.text
    except Exception:
        pass
    # Method 2
    for ua in USER_AGENTS[1:]:
        try:
            res = requests.get(url, headers={"User-Agent": ua, "Referer": "https://www.google.com/"}, timeout=TIMEOUT)
            if res.status_code == 200:
                return res.text
        except Exception:
            pass
    # Method 3: Backoff retries
    for delay in [2, 4]:
        time.sleep(delay)
        try:
            res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=TIMEOUT)
            if res.status_code == 200:
                return res.text
        except Exception:
            pass
    return ""

def _clean(html: str) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "svg", "iframe", "footer", "header", "nav", "noscript"]):
        tag.decompose()
    blocks = []
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
        text = tag.get_text().strip()
        if text:
            text = re.sub(r'\s+', ' ', text)
            if text not in blocks:
                blocks.append(text)
    return "\n".join(blocks)

def _extract_contacts(html: str, base_domain: str) -> Dict[str, Any]:
    # Emails
    emails = list(set(re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', html)))
    emails = [e.lower() for e in emails if not e.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"))]
    
    # Phone
    phone = ""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()
    phone_candidates = re.findall(r'\+?\b\d{1,4}[-.\s]?\(?\d{1,3}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b', text)
    for candidate in phone_candidates:
        try:
            parsed = phonenumbers.parse(candidate, "US")
            if phonenumbers.is_valid_number(parsed):
                phone = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
                break
        except Exception:
            continue
            
    # Address
    address = ""
    for tag in soup.find_all("address"):
        addr_text = tag.get_text(separator=" ").strip()
        if len(addr_text) > 10:
            address = re.sub(r'\s+', ' ', addr_text)
            break
            
    return {"emails": emails, "phone": phone, "address": address}

# ========= REQUIRED FUNCTION =========
def enrich_company(url: str) -> dict:
    """
    Input: Company URL
    Output: Structured company profile (STRICT FORMAT)
    """
    normalized_url = _normalize_url(url)
    if not normalized_url:
        return {
            "website_name": url,
            "company_name": "",
            "address": "",
            "mobile_number": "",
            "mail": [],
            "core_service": "",
            "target_customer": "",
            "probable_pain_point": "",
            "outreach_opener": ""
        }
        
    base_domain = _get_base_domain(normalized_url)
    
    # 1. Scrape Homepage & Discover Pages
    homepage_html = _scrape(normalized_url)
    if not homepage_html:
        return {
            "website_name": base_domain,
            "company_name": base_domain.split(".")[0].title(),
            "address": "",
            "mobile_number": "",
            "mail": [],
            "core_service": "",
            "target_customer": "",
            "probable_pain_point": "",
            "outreach_opener": ""
        }
        
    discovered_urls = _score_links(_extract_links(homepage_html, normalized_url), normalized_url)
    
    # Scrape all selected pages
    pages_html = {normalized_url: homepage_html}
    for p in discovered_urls:
        if p == normalized_url:
            continue
        h = _scrape(p)
        if h:
            pages_html[p] = h
            
    # Extract data and clean content
    combined_texts = []
    all_emails = set()
    best_phone = ""
    best_address = ""
    
    for page, html in pages_html.items():
        contacts = _extract_contacts(html, base_domain)
        all_emails.update(contacts["emails"])
        if contacts["phone"] and not best_phone:
            best_phone = contacts["phone"]
        if contacts["address"] and not best_address:
            best_address = contacts["address"]
            
        cleaned = _clean(html)
        if cleaned:
            p_name = urllib.parse.urlparse(page).path.strip("/") or "Home"
            combined_texts.append(f"--- PAGE: {p_name.upper()} ---\n{cleaned}")
            
    full_content = re.sub(r'\n{3,}', '\n\n', "\n\n".join(combined_texts))
    if len(full_content) > 4800:
        full_content = full_content[:4800] + "\n[Content Truncated...]"
        
    company_name_fallback = base_domain.split(".")[0].title()
    
    # 2. LLM Groq Analysis
    system_prompt = """You are a professional business information extraction engine.

Strictly adhere to the following rules:
1. Use ONLY the supplied website content. Do not assume or extrapolate beyond direct textual facts.
2. Never fabricate/hallucinate email addresses, phone numbers, or addresses.
3. If specific contact details (email, phone, address) are missing from the content, use the extracted contact details provided in the prompt. If still missing, return "".
4. If a field cannot be answered with absolute certainty from the text, return "".
5. For "core_service" and "target_customer", give high-quality concise descriptions based strictly on the text.
6. For "probable_pain_point", analyze the problems their clients solve with their services, referencing the text.
7. For "outreach_opener", construct an engaging, personalized cold outreach opener line suitable for sales development.
8. Return ONLY valid JSON matching the exact schema. No markdown, no explanations, and no extra keys.

Response Schema:
{
  "website_name": "string",
  "company_name": "string",
  "address": "string",
  "mobile_number": "string",
  "mail": ["string"],
  "core_service": "string",
  "target_customer": "string",
  "probable_pain_point": "string",
  "outreach_opener": "string"
}"""

    user_prompt = f"""Target Website URL: {url}

=== SCRAPED WEBSITE CONTENT ===
{full_content}

=== PRE-EXTRACTED CONTACT DETAILS ===
Address: {best_address}
Phone: {best_phone}
Emails: {list(all_emails)}

Instructions: Analyze the website content and pre-extracted contact details. Populate the JSON schema. Use empty string or empty lists where facts are missing. Avoid fabrication of facts. Use exact keys.
"""

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }
    
    fallback_dict = {
        "website_name": base_domain,
        "company_name": company_name_fallback,
        "address": best_address,
        "mobile_number": best_phone,
        "mail": list(all_emails),
        "core_service": "",
        "target_customer": "",
        "probable_pain_point": "",
        "outreach_opener": ""
    }

    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=20)
        if response.status_code == 200:
            res_json = response.json()
            raw_text = res_json["choices"][0]["message"]["content"].strip()
            parsed_data = json.loads(raw_text)
            validated = CompanyProfile.model_validate(parsed_data)
            return validated.model_dump()
        else:
            # Retry once
            payload["temperature"] = 0.05
            response_retry = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=20)
            if response_retry.status_code == 200:
                res_json = response_retry.json()
                raw_text = res_json["choices"][0]["message"]["content"].strip()
                parsed_data = json.loads(raw_text)
                validated = CompanyProfile.model_validate(parsed_data)
                return validated.model_dump()
    except Exception:
        pass
        
    return fallback_dict

# ========= 9. MAIN EXECUTION =========
if __name__ == "__main__":
    # 👉 Replace with provided company URLs
    urls = [
        "https://fireflies.ai",
        "https://example.com"
    ]

    results = []

    for url in urls:
        print(f"Enriching company URL: {url}...")
        try:
            data = enrich_company(url)
            results.append(data)
        except Exception as e:
            print(f"Error processing {url}: {e}")

    # Save results to JSON file
    output_filepath = "results.json"
    with open(output_filepath, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved results to {output_filepath}")

    # Print results for evaluation
    print("\n=== FINAL OUTPUT ===\n")
    for r in results:
        print(json.dumps(r, indent=2))
