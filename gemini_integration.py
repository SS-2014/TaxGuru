import requests
import json
import time
import re
from functools import lru_cache

MODEL = "gemini-1.5-flash"

BASE_PROMPT = """You are TaxGPT, an intelligent AI assistant for Indian taxation and finance.

You behave like ChatGPT + Perplexity:
- You can reason step-by-step
- You can simulate web search
- You can give real recommendations

STYLE:
- Be crisp
- Use bullet points
- Give direct answers first

You are allowed to recommend financial products.
"""

@lru_cache(maxsize=100)
def call_llm(prompt, api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={api_key}"

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 700,
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

def extract_text(res):
    try:
        return res["candidates"][0]["content"]["parts"][0]["text"]
    except:
        return ""

def detect_intent(query, api_key):
    prompt = f"""
Classify the user query into one of these:
- TAX_CALCULATION
- TAX_ADVICE
- FINANCIAL_RECOMMENDATION
- GENERAL

Return only the label.

Query: {query}
"""
    res = call_llm(prompt, api_key)
    return extract_text(res).strip()

def create_plan(query, intent, api_key):
    prompt = f"""
You are an AI planner.

Query: {query}
Intent: {intent}

Create a short step-by-step plan (3-5 steps).
"""
    res = call_llm(prompt, api_key)
    return extract_text(res)

def search_tool(query, api_key):
    prompt = f"""
Simulate a web search and provide real-world info, names, and data.

Query: {query}
"""
    res = call_llm(prompt, api_key)
    return extract_text(res)

def tax_tool(query, api_key):
    prompt = f"""
Answer using Indian tax rules.

Query: {query}
"""
    res = call_llm(prompt, api_key)
    return extract_text(res)

def generate_final_answer(query, context, api_key):
    prompt = f"""
{BASE_PROMPT}

User Query:
{query}

Context:
{context}

Provide:
1. Direct answer
2. Recommendations (if relevant)
3. Reasoning
"""
    res = call_llm(prompt, api_key)
    return extract_text(res)

def run_agent(query, api_key):
    intent = detect_intent(query, api_key)
    plan = create_plan(query, intent, api_key)

    context = f"Plan:\n{plan}\n\n"

    if intent == "FINANCIAL_RECOMMENDATION":
        context += search_tool(query, api_key)
    elif intent in ["TAX_ADVICE", "TAX_CALCULATION"]:
        context += tax_tool(query, api_key)
    else:
        context += search_tool(query, api_key)

    return generate_final_answer(query, context, api_key)

def analyze_document(image_bytes, api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={api_key}"

    prompt = """
Extract salary details.

Return JSON:
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
        "contents": [{"parts": [{"text": prompt}]}]
    }

    try:
        res = requests.post(url, json=payload)
        text = res.json()["candidates"][0]["content"]["parts"][0]["text"]

        match = re.search(r"\{.*\}", text, re.DOTALL)

        if match:
            return json.loads(match.group())

        return {"error": "Parsing failed"}
    except Exception as e:
        return {"error": str(e)}
