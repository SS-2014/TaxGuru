import requests
import json
import time
import re
from functools import lru_cache

SYSTEM_PROMPT_TAX_ADVISOR = """You are TaxGPT, a sharp, concise AI assistant and Indian tax advisor.

You behave like ChatGPT with strong reasoning, but with deep expertise in Indian taxation.

STYLE:
- Be crisp, structured, and helpful
- Avoid long paragraphs
- Use bullet points where useful
- Answer directly first, then explain

CAPABILITIES:
1. Answer general questions
2. Provide Indian tax advice
3. Combine both when needed

RULES:
- Cite tax sections ONLY when relevant
- If not tax-related, answer normally
- If unsure, say so
"""

def web_search(query: str) -> str:
    try:
        url = f"https://api.duckduckgo.com/?q={query}&format=json"
        res = requests.get(url).json()

        if res.get("AbstractText"):
            return res["AbstractText"]

        for topic in res.get("RelatedTopics", [])[:3]:
            if isinstance(topic, dict) and topic.get("Text"):
                return topic["Text"]

        return ""
    except:
        return ""

def clean_response(text):
    return text.replace("\n\n\n", "\n\n").strip()

@lru_cache(maxsize=100)
def cached_llm_call(full_prompt, model, api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    payload = {
        "contents": [{"role": "user", "parts": [{"text": full_prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "topP": 0.8,
            "maxOutputTokens": 512,
        }
    }

    for i in range(3):
        try:
            response = requests.post(url, json=payload, timeout=30)

            if response.status_code == 200:
                return response
            elif response.status_code == 429:
                time.sleep(2 ** i)
        except:
            time.sleep(2 ** i)

    return None

def call_gemini(prompt, api_key, model="gemini-1.5-flash"):
    web_context = web_search(prompt)

    full_prompt = f"""
{SYSTEM_PROMPT_TAX_ADVISOR}

WEB CONTEXT:
{web_context}

USER QUERY:
{prompt}
"""

    response = cached_llm_call(full_prompt, model, api_key)

    if not response:
        return "API Error. Please try again later."

    try:
        data = response.json()
        output_text = data["candidates"][0]["content"]["parts"][0]["text"]
        return clean_response(output_text)
    except:
        return "Error parsing response."

def analyze_document(image_bytes, api_key, mime_type="image/png"):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"

    prompt = """
Extract structured salary details from this payslip.

Return ONLY JSON with:
{
 "gross_salary": number,
 "basic_salary": number,
 "hra": number,
 "tds_deducted": number,
 "section_80c_total": number,
 "section_80d": number,
 "period": "monthly" or "annual"
}
"""

    payload = {
        "contents": [{
            "parts": [
                {"text": prompt}
            ]
        }]
    }

    try:
        response = requests.post(url, json=payload)

        if response.status_code != 200:
            return {"error": "API failure"}

        text = response.json()["candidates"][0]["content"]["parts"][0]["text"]

        json_match = re.search(r'\{.*\}', text, re.DOTALL)

        if json_match:
            return json.loads(json_match.group())

        return {"error": "Could not parse JSON"}

    except Exception as e:
        return {"error": str(e)}
