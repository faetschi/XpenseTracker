from app.core.config import settings

categories_str = ", ".join(settings.EXPENSE_CATEGORIES)
income_categories_str = ", ".join(settings.INCOME_CATEGORIES)

RECEIPT_ANALYSIS_PROMPT = f"""
Analyze this receipt image. Extract the following fields in JSON format: 
'date' (DD.MM.YYYY),
'total_amount' (float), 
'currency' (ISO code), 
    - 'category' (guess based on items: {categories_str}), 
and 'description' (shop name). 
If the currency is not EUR, return 'UNKNOWN' for the currency field.
Return ONLY the raw JSON string, no markdown formatting.
"""

BANK_CATEGORY_MAPPING_PROMPT = f"""
You assign categories for bank transactions.
Allowed expense categories: {categories_str}
Allowed income categories: {income_categories_str}

Input is JSON array of objects with fields:
- id (integer)
- description (string)

Return ONLY a JSON array of objects with fields:
- id
- category (must be one of the allowed categories)

Use transaction description as the primary signal.
Merchant examples to map consistently:
- "GMS - OSTERR. KONTROLL" -> prefer "OeKB" (or "Rechnungen/Fixkosten" if OeKB is not available)
- "HOFER" -> "Lebensmittel"
- "THERME LAA SILENT SPA" -> best fit from travel/leisure/health categories (prefer "Reisen" when available)

For recurring merchants, keep category choices consistent across rows.

If you are unsure, use "Sonstiges" if available, otherwise use the first allowed category.
"""
