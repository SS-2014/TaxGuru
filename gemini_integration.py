import requests
import json
import time
import re
import os
import base64
from functools import lru_cache

MODEL = "gemini-2.5-flash"

# =========================
# SYSTEM PROMPT (VERY IMPORTANT)
# =========================
SYSTEM_PROMPT = """You are TaxGPT, an expert AI assistant for Indian taxation and financial planning.

You behave like ChatGPT + Perplexity:
- You reason step-by-step internally
- You provide real-world recommendations
- You simulate web knowledge when needed

STYLE:
- Be crisp and practical
- Give direct answers first
- Use bullet points
- Avoid generic disclaimers

CAPABILITIES:
- Tax advice (Indian Income Tax Act)
- Financial recommendations (NPS, ELSS, insurance)
- Compare options and suggest best choices

IMPORTANT:
- ALWAYS give specific recommendations when asked
- Use real examples (fund names, schemes, strategies)
- If unsure, give best possible answer instead of refusing

OUTPUT FORMAT:
1. Direct Answer
2. Top Recommendations (if applicable)
3. Reasoning
4. Optional: Tax Saving Tips
"""

# =========================
# CACHE (CRITICAL)
# =========================
#@lru_cache(maxsize=200)
def cached_call(prompt, api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={api_key}"

    payload = {
    "contents": [
        {
            "role": "user",
            "parts": [{"text": prompt}]
        }
    ],
    "generationConfig": {
        "temperature": 0.5,
        "topP": 0.9,
        "maxOutputTokens": 800,
    }
}
    for i in range(3):
        try:
            res = requests.post(url, json=payload, timeout=30)

            if res.status_code == 200:
                return res.json()

            elif res.status_code == 429:
                time.sleep(2 ** i)

        except:
            time.sleep(2 ** i)

    return None

# =========================
# SINGLE-CALL AGENT
# =========================
def call_agent(user_query, api_key, user_profile=None):

    profile_context = ""
    if user_profile:
        profile_context = f"""
User Financial Profile:
{json.dumps(user_profile, indent=2)}
"""

    prompt = f"""
{SYSTEM_PROMPT}

{profile_context}

INSTRUCTIONS:
- Think step-by-step internally before answering
- Use tax knowledge + general knowledge
- If user asks for "best", "top", "recommend":
    → give specific names and ranked suggestions
- If tax related:
    → include sections + savings opportunities

USER QUERY:
{user_query}
"""

    response = cached_call(prompt, api_key)

    if not response:
        return "⚠️ API error. Please try again."

    try:
        text = response["candidates"][0]["content"]["parts"][0]["text"]
        return text.strip()
    except:
        return "⚠️ Error parsing response"


# =========================
# IMAGE ANALYSIS (FLASH SUPPORT)
# =========================
def analyze_document(image_bytes, api_key, mime_type="image/png"):

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={api_key}"

    prompt = """
Extract structured salary details from this payslip.

Return ONLY valid JSON:
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
    encoded_image = base64.b64encode(image_bytes).decode("utf-8")
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": encoded_image
                        }
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "topP": 0.9,
            "maxOutputTokens": 1000
        }
    }

    try:
        res = requests.post(url, json=payload)

        if res.status_code != 200:
            return {"error": "API failure"}

        data = res.json()
        if "candidates" not in data:
            return {"error": str(data)}
        text = data["candidates"][0]["content"]["parts"][0]["text"]

        match = re.search(r"\{.*\}", text, re.DOTALL)

        if match:
            return json.loads(match.group())

        return {"error": "Parsing failed"}

    except Exception as e:
        return {"error": str(e)}
