"""
TaxGuru AI Engine — Powered by Groq
Uses:
  - llama-3.3-70b-versatile: Main chat (fast, smart, free tier ~30 RPM)
  - meta-llama/llama-4-scout-17b-16e-instruct: Vision/document analysis
  - compound-beta: Web search when needed
All via OpenAI-compatible REST API — no SDK needed.
"""

import re
import json
import os
import requests
import base64

GROQ_BASE = "https://api.groq.com/openai/v1/chat/completions"

# ── System Prompts ──

SYSTEM_PROMPT_TAX_ADVISOR = """You are {agent_name}, a personal Indian income tax advisor on the TaxGuru platform, for FY 2025-26 (AY 2026-27).

CORE PRINCIPLES:
1. ACCURACY FIRST: Only provide advice grounded in the Income Tax Act (1961 and 2025), Finance Acts, CBDT circulars, and established case law. If you are unsure, say so clearly.
2. CITE SECTIONS: Always reference specific sections (e.g., "Section 80C", "Section 112A", "Rule 11UA"). This builds trust and lets users verify.
3. DUAL REGIME AWARENESS: India has two tax regimes — Old (with deductions) and New (lower rates, limited deductions). Always consider both when relevant.
4. PRACTICAL ADVICE: Don't just explain the law — tell the user what to DO. Recommend specific actions, investments, or filings.
5. TONE: Professional, warm, helpful. Speak as {agent_name}. Use first person ("I recommend...", "Based on your numbers, I see that..."). Not robotic or overly formal.
6. PRIVACY: Never ask for or reference PAN, Aadhaar, bank accounts, employer names, or personal identifiers. Work only with financial numbers.
7. CURRENT LAW: Apply FY 2025-26 rules including Budget 2025 changes (new regime default, ₹12.75L tax-free, 87A rebate ₹60K, standard deduction ₹75K, capital gains changes).
8. MULTILINGUAL: When responding in Hindi, Tamil, Telugu, or Kannada, keep tax terminology in English in parentheses for clarity. Refer to yourself as {agent_name} in all languages.
9. PRODUCT RECOMMENDATIONS: When suggesting investments or insurance, give specific product names, expected returns, and lock-in periods available in India (e.g., "Mirae Asset ELSS Fund — ~15% 3yr CAGR, 3yr lock-in").
10. WEB SEARCH: If the user asks about very recent developments, latest CBDT circulars, or current market rates, and you have web search context, use it to give the most current answer.

KEY FY 2025-26 FACTS:
- New Regime Slabs: 0-4L: Nil, 4-8L: 5%, 8-12L: 10%, 12-16L: 15%, 16-20L: 20%, 20-24L: 25%, 24L+: 30%
- Old Regime: 0-2.5L: Nil (0-3L for seniors), 2.5-5L: 5%, 5-10L: 20%, 10L+: 30%
- 87A Rebate: ₹60,000 (new), ₹12,500 (old)
- Standard Deduction: ₹75,000 (new), ₹50,000 (old)
- 80C: Max ₹1.5L | 80D: ₹25K self + ₹50K parents (senior) | 80CCD(1B): ₹50K NPS
- LTCG equity: 12.5% above ₹1.25L | STCG equity: 20%
- HRA: 8 metro cities from April 2026 (IT Rules 2026)
- ESOP deferral: 48 months or exit, whichever earlier
"""

SYSTEM_PROMPT_DOCUMENT_ANALYZER = """You are a document analysis agent for TaxGuru. You extract financial data from Indian payslips, Form 16, and employer tax statements.

DOCUMENT TYPES YOU HANDLE:
1. PAYSLIP (monthly): Contains one month's salary breakdown. You must indicate "period": "monthly" so we can annualize.
2. FORM 16 (annual): Issued by employer, contains full-year salary, deductions, and TDS. Indicate "period": "annual".
3. TAX COMPUTATION STATEMENT (annual): Employer's tax projection. Indicate "period": "annual".

EXTRACT these fields (use 0 if not found, "NOT_FOUND" only if the document type should have it but it's illegible):
- gross_salary: Total gross salary/earnings
- basic_salary: Basic pay component
- hra: House Rent Allowance
- special_allowance: Special/flexible/FBP allowance
- lta: Leave Travel Allowance
- pf_employee: Employee PF/provident fund contribution
- pf_employer: Employer PF contribution
- professional_tax: Professional tax deducted
- tds_deducted: Income tax / TDS deducted
- standard_deduction: Standard deduction (usually 50000 or 75000 if shown)
- section_80c_total: Total 80C investments if shown (EPF + PPF + ELSS + LIC etc.)
- section_80d: Health insurance premium if shown
- section_80ccd_1b: NPS employee additional if shown
- section_80ccd_2: NPS employer contribution if shown
- section_24b: Home loan interest if shown
- other_income: Any other income mentioned
- net_taxable_income: Net taxable income if computed in document
- tax_old_regime: Tax under old regime if shown
- tax_new_regime: Tax under new regime if shown
- period: "monthly" or "annual" — CRITICAL, determines if we multiply by 12

RULES:
1. Extract exact numbers. Do not estimate or round.
2. NEVER extract or return: names, PAN, Aadhaar, employee ID, employer name, address, bank account, UAN.
3. If a field is not present in the document, use 0.
4. Return ONLY a valid JSON object with these fields. No explanation text.
5. For monthly payslips: basic, hra, allowances are monthly amounts. gross_salary is the monthly total.
"""


# ── Privacy Layer ──

PERSONAL_PATTERNS = [
    (r'\b[A-Z]{5}\d{4}[A-Z]\b', '[PAN_REDACTED]'),
    (r'\b\d{4}\s?\d{4}\s?\d{4}\b', '[AADHAAR_REDACTED]'),
    (r'\b\d{10,12}\b', '[PHONE/ACCT_REDACTED]'),
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REDACTED]'),
    (r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', '[DATE_REDACTED]'),
    (r'(?i)\b(?:mr|mrs|ms|dr|shri|smt)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', '[NAME_REDACTED]'),
]

def anonymize_text(text: str) -> tuple:
    """Remove personal identifiers from text. Returns (cleaned_text, redactions_made)."""
    redactions = []
    cleaned = text
    for pattern, replacement in PERSONAL_PATTERNS:
        matches = re.findall(pattern, cleaned)
        if matches:
            redactions.extend(matches)
            cleaned = re.sub(pattern, replacement, cleaned)
    return cleaned, redactions


def extract_financial_only(profile_dict: dict) -> dict:
    """Extract only financial fields from a profile dict, removing any personal info."""
    financial_keys = {
        'taxpayer_type', 'age', 'residency', 'metro_city',
        'gross_salary', 'basic_salary', 'hra_received', 'rent_paid_annual',
        'business_income', 'professional_income', 'trading_income',
        'interest_income', 'rental_income', 'dividend_income',
        'stcg_equity', 'stcg_other', 'ltcg_equity', 'ltcg_other',
        'esop_perquisite', 'foreign_esop',
        'section_80c', 'section_80d_self', 'section_80d_parents',
        'section_80ccd_1b', 'section_80ccd_2', 'section_80e',
        'section_80g', 'section_24b', 'section_80tta',
        'tds_deducted', 'advance_tax_paid', 'lta',
    }
    return {k: v for k, v in profile_dict.items() if k in financial_keys and v}


# ── Groq API Calls ──

def _get_api_key():
    """Get Groq API key from env or st.secrets."""
    key = os.environ.get("GROQ_API_KEY", "")
    if not key:
        try:
            import streamlit as st
            key = st.secrets.get("GROQ_API_KEY", "")
        except:
            pass
    return key


def call_groq_chat(messages: list, model: str = "llama-3.3-70b-versatile",
                    api_key: str = None, temperature: float = 0.3,
                    max_tokens: int = 1024) -> str:
    """Call Groq chat completion API."""
    if not api_key:
        api_key = _get_api_key()
    if not api_key:
        return "⚠️ GROQ_API_KEY not configured."

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        resp = requests.post(GROQ_BASE, headers=headers, json=payload, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            return data['choices'][0]['message']['content']
        else:
            err = resp.json().get('error', {}).get('message', resp.text[:200])
            return f"⚠️ API error ({resp.status_code}): {err}"
    except Exception as e:
        return f"⚠️ Connection error: {str(e)}"


def call_gemini(prompt: str, system_prompt: str = SYSTEM_PROMPT_TAX_ADVISOR,
                context: str = "", language: str = "en",
                api_key: str = None, model: str = "llama-3.3-70b-versatile",
                agent_name: str = "TaxGuru AI") -> str:
    """
    Main chat function — drop-in replacement for old Gemini version.
    Same signature so app.py doesn't need changes.
    """
    # Get Groq key (not Gemini key)
    groq_key = os.environ.get("GROQ_API_KEY", "")
    if not groq_key:
        try:
            import streamlit as st
            groq_key = st.secrets.get("GROQ_API_KEY", "")
        except:
            pass
    # Fallback: try the old GEMINI_API_KEY name in case user hasn't updated secrets
    if not groq_key:
        groq_key = api_key or ""
    if not groq_key:
        return "⚠️ API key not configured. Add GROQ_API_KEY to secrets."

    resolved_system = system_prompt.replace("{agent_name}", agent_name)

    lang_instruction = ""
    if language != "en":
        lang_map = {"hi": "Hindi", "ta": "Tamil", "te": "Telugu", "kn": "Kannada"}
        lang_name = lang_map.get(language, "English")
        lang_instruction = f"\n\nIMPORTANT: Respond in {lang_name}. Keep tax terms in English in parentheses."

    user_content = prompt
    if context:
        user_content = f"""KNOWLEDGE BASE CONTEXT (use this to ground your answer):
{context}

USER QUESTION: {prompt}"""

    messages = [
        {"role": "system", "content": resolved_system + lang_instruction},
        {"role": "user", "content": user_content}
    ]

    return call_groq_chat(messages, model="llama-3.3-70b-versatile",
                          api_key=groq_key, temperature=0.3, max_tokens=1024)


def analyze_document(image_bytes: bytes, api_key: str, mime_type: str = "image/jpeg") -> dict:
    """Analyze a payslip/Form 16 image using Groq Vision (Llama 4 Scout)."""

    groq_key = os.environ.get("GROQ_API_KEY", "")
    if not groq_key:
        try:
            import streamlit as st
            groq_key = st.secrets.get("GROQ_API_KEY", "")
        except:
            pass
    if not groq_key:
        groq_key = api_key or ""
    if not groq_key:
        return {"error": "GROQ_API_KEY not configured"}

    b64_data = base64.b64encode(image_bytes).decode('utf-8')

    # Map common MIME types
    if 'pdf' in mime_type.lower():
        return {"error": "PDF upload not supported for vision. Please upload as image (JPG/PNG)."}

    headers = {
        "Authorization": f"Bearer {groq_key}",
        "Content-Type": "application/json"
    }

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT_DOCUMENT_ANALYZER + "\n\nExtract all financial data from this payslip/Form 16 document. Return ONLY a JSON object with the extracted fields. No personal identifiers. No explanation text — just the JSON."
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{b64_data}"
                    }
                }
            ]
        }
    ]

    payload = {
        "model": "meta-llama/llama-4-scout-17b-16e-instruct",
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 1024,
    }

    try:
        resp = requests.post(GROQ_BASE, headers=headers, json=payload, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            text = data['choices'][0]['message']['content']
            # Try to parse JSON from response
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                return json.loads(json_match.group())
            return {"raw_text": text, "parse_error": "Could not extract structured data"}
        else:
            err_body = resp.text[:300]
            return {"error": f"Vision API error ({resp.status_code}): {err_body}"}
    except Exception as e:
        return {"error": str(e)}


# ── RAG Query Builder ──

def build_rag_query(user_question: str, taxpayer_profile: dict = None) -> dict:
    """Build a RAG-enhanced query with relevant knowledge base context."""
    from knowledge_base import search_knowledge, format_for_llm_context, get_for_taxpayer_type

    question_lower = user_question.lower()

    keyword_map = {
        '80c': 'section_80c', 'elss': 'section_80c', 'ppf': 'section_80c', 'epf': 'section_80c',
        '80d': 'section_80d', 'health insurance': 'section_80d', 'mediclaim': 'section_80d',
        'nps': 'section_80ccd', '80ccd': 'section_80ccd',
        'hra': 'hra_exemption', 'house rent': 'hra_exemption',
        'home loan': 'home_loan', '24b': 'home_loan', 'housing loan': 'home_loan',
        'capital gain': 'capital_gains_2024', 'ltcg': 'capital_gains_2024', 'stcg': 'capital_gains_2024',
        'new regime': 'new_regime_default', 'old regime': 'old_regime_deductions',
        '87a': 'section_87a_marginal', 'rebate': 'section_87a_marginal',
        'esop': 'esop_taxation', 'stock option': 'esop_taxation', 'rsu': 'esop_taxation',
        'nri': 'nri_taxation', 'non resident': 'nri_taxation', 'residency': 'residency_rules',
        'business': 'business_presumptive', 'professional': 'professional_presumptive',
        'f&o': 'fno_taxation', 'futures': 'fno_taxation', 'trading': 'fno_taxation',
        'crypto': 'crypto_vda', 'bitcoin': 'crypto_vda', 'vda': 'crypto_vda',
        'budget': 'budget_2025', 'surcharge': 'surcharge_2025',
        'itr': 'itr_forms', 'filing': 'itr_forms', 'return': 'itr_forms',
        'advance tax': 'advance_tax', 'tds': 'tds_rates',
        'hra 8 cities': 'hra_8_cities', 'metro': 'hra_8_cities',
        'form 16': 'form_16', 'salary slip': 'form_16',
        'agricultural': 'agricultural_income', 'farm': 'agricultural_income',
        'refund': 'refund_delays', 'delay': 'refund_delays',
        'scrutiny': 'cbdt_scrutiny_2025',
        'it rules 2026': 'it_rules_2026', 'tax year': 'tax_year_concept',
    }

    matched_keys = set()
    for keyword, kb_key in keyword_map.items():
        if keyword in question_lower:
            matched_keys.add(kb_key)

    # Also do semantic search
    search_results = search_knowledge(user_question)
    for key, _, _ in search_results[:3]:
        matched_keys.add(key)

    # Add profile-specific context
    if taxpayer_profile:
        tp_type = taxpayer_profile.get('taxpayer_type', 'salaried')
        type_keys = get_for_taxpayer_type(tp_type)
        matched_keys.update(type_keys[:2])

    # Build context from matched keys
    context = format_for_llm_context(list(matched_keys)[:8])

    # Add profile summary if available
    profile_context = ""
    if taxpayer_profile:
        non_zero = {k: v for k, v in taxpayer_profile.items() if v and v != 0 and k != 'taxpayer_type'}
        if non_zero:
            profile_context = "\n\nUSER'S TAX PROFILE:\n"
            for k, v in non_zero.items():
                profile_context += f"- {k.replace('_', ' ').title()}: {v}\n"

    return {
        "context": context + profile_context,
        "matched_keys": list(matched_keys),
        "has_profile": bool(taxpayer_profile),
    }
