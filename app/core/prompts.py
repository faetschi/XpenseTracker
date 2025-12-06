from app.core.config import settings

categories_str = ", ".join(settings.EXPENSE_CATEGORIES)

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
