import json
import re
from typing import Dict, List, Tuple

import google.genai as genai
from openai import OpenAI

from app.core.config import settings
from app.core.prompts import BANK_CATEGORY_MAPPING_PROMPT
from app.utils.logger import get_logger
from app.utils.bank_csv import BankCsvEntry

logger = get_logger(__name__)


def _default_category(entry_type: str) -> str:
    if entry_type == "transfer":
        return "Transfer"
    if entry_type == "income":
        return settings.INCOME_CATEGORIES[0] if settings.INCOME_CATEGORIES else "Sonstiges"
    return settings.EXPENSE_CATEGORIES[0] if settings.EXPENSE_CATEGORIES else "Sonstiges"


def _resolve_category(candidates: List[str], entry_type: str) -> str:
    if entry_type == "transfer":
        return "Transfer"
    allowed = settings.INCOME_CATEGORIES if entry_type == "income" else settings.EXPENSE_CATEGORIES
    allowed_lower = {c.lower(): c for c in allowed}

    for candidate in candidates:
        if candidate.lower() in allowed_lower:
            return allowed_lower[candidate.lower()]

    # Try partial matching, e.g. "OeKB" against "OeKB/Job"
    for candidate in candidates:
        needle = candidate.lower()
        for allowed_cat in allowed:
            if needle in allowed_cat.lower() or allowed_cat.lower() in needle:
                return allowed_cat

    return _default_category(entry_type)


def _heuristic_category_for_description(description: str, entry_type: str) -> str:
    text = (description or "").lower()

    if entry_type == "transfer":
        return "Transfer"
    if entry_type == "income":
        if any(k in text for k in ("gehalt", "salary", "lohn")):
            return _resolve_category(["Gehalt"], entry_type)
        return _default_category(entry_type)

    if "gms - osterr" in text or "oekb" in text or "kontrollbank" in text:
        return _resolve_category(["OeKB", "Rechnungen/Fixkosten"], entry_type)
    if "hofer" in text or "billa" in text or "spar" in text or "lidl" in text:
        return _resolve_category(["Lebensmittel"], entry_type)
    if "therme" in text or "silent spa" in text or "spa" in text:
        return _resolve_category(["Reisen", "Unterhaltung", "Gesundheit"], entry_type)
    if "kino" in text or "cinema" in text:
        return _resolve_category(["Unterhaltung"], entry_type)
    if "uber" in text or "taxi" in text or "wiener linien" in text:
        return _resolve_category(["Transport"], entry_type)
    if "miete" in text or "rent" in text:
        return _resolve_category(["Miete", "Rechnungen/Fixkosten"], entry_type)

    return _default_category(entry_type)


def _chunk_entries(entries: List, size: int) -> List[List]:
    return [entries[i:i + size] for i in range(0, len(entries), size)]


def _apply_recurring_overrides(entries: List[BankCsvEntry], mapping: Dict[int, str]) -> Dict[int, str]:
    rules = settings.BANK_RECURRING_MAPPINGS or []
    if not rules:
        return mapping

    for idx, entry in enumerate(entries, start=1):
        if entry.entry_type == "transfer":
            continue
        description = (entry.description or "").lower()
        for rule in rules:
            contains = str(rule.get("contains", "")).strip().lower()
            category = str(rule.get("category", "")).strip()
            if contains and category and contains in description:
                mapping[idx] = category
                break

    return mapping


def apply_recurring_mappings_to_entries(entries: List[BankCsvEntry]) -> None:
    """Apply recurring description override rules directly to entry categories in-place."""
    temp_mapping: Dict[int, str] = {
        idx: entry.category
        for idx, entry in enumerate(entries, start=1)
    }
    resolved = _apply_recurring_overrides(entries, temp_mapping)
    for idx, entry in enumerate(entries, start=1):
        override = resolved.get(idx)
        if override:
            entry.category = override


def _parse_ai_json(content: str) -> List[dict]:
    raw = (content or '').strip()
    if raw.startswith('```json'):
        raw = raw[7:]
    elif raw.startswith('```'):
        raw = raw[3:]
    if raw.endswith('```'):
        raw = raw[:-3]
    raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        # Fallback: extract first JSON array from mixed text responses.
        match = re.search(r"\[[\s\S]*\]", raw)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        logger.error(f"AI mapping returned invalid JSON: {exc}; content={raw[:400]}")
        raise ValueError("AI mapping returned invalid JSON")


def _call_openai(client: OpenAI, payload: List[dict]) -> List[dict]:
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": BANK_CATEGORY_MAPPING_PROMPT},
            {"role": "user", "content": json.dumps(payload)},
        ],
        max_tokens=600,
    )

    content = response.choices[0].message.content or "[]"
    return _parse_ai_json(content)


def _call_gemini(client: genai.Client, payload: List[dict]) -> List[dict]:
    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=[BANK_CATEGORY_MAPPING_PROMPT, json.dumps(payload)]
    )

    return _parse_ai_json(response.text or "[]")


def map_bank_categories(entries: List[BankCsvEntry]) -> Dict[int, str]:
    provider = settings.AI_PROVIDER.lower()
    client_openai = None
    client_gemini = None

    if provider == "testing":
        heuristic_mapping = {
            idx: _heuristic_category_for_description(entry.description, entry.entry_type)
            for idx, entry in enumerate(entries, start=1)
        }
        return _apply_recurring_overrides(entries, heuristic_mapping)

    if provider == "openai":
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not configured")
        client_openai = OpenAI(api_key=settings.OPENAI_API_KEY)
    elif provider == "gemini":
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is not configured")
        client_gemini = genai.Client(api_key=settings.GOOGLE_API_KEY)
    else:
        raise ValueError("Unsupported AI provider for mapping")

    mapping: Dict[int, str] = {}

    for idx, entry in enumerate(entries, start=1):
        if entry.entry_type == "transfer":
            mapping[idx] = "Transfer"

    non_transfer = [(idx, e) for idx, e in enumerate(entries, start=1) if e.entry_type != "transfer"]
    offset = 0
    for chunk in _chunk_entries(non_transfer, 50):
        payload = [
            {"id": idx + offset + 1, "description": entry.description}
            for idx, (_, entry) in enumerate(chunk)
        ]
        if provider == "openai":
            parsed = _call_openai(client_openai, payload)
        else:
            parsed = _call_gemini(client_gemini, payload)
        for item in parsed:
            try:
                row_id = int(item.get("id"))
                category = str(item.get("category", "")).strip()
                original_idx, entry = non_transfer[row_id - 1]
            except Exception:
                continue

            allowed = settings.INCOME_CATEGORIES if entry.entry_type == "income" else settings.EXPENSE_CATEGORIES
            if category not in allowed:
                category = _default_category(entry.entry_type)

            mapping[original_idx] = category

        offset += len(chunk)

    for idx, entry in enumerate(entries, start=1):
        if idx not in mapping:
            mapping[idx] = _default_category(entry.entry_type)

    return _apply_recurring_overrides(entries, mapping)
