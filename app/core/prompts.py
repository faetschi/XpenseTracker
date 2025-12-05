RECEIPT_ANALYSIS_PROMPT = """
Analyze this receipt image. Extract the following fields in JSON format: 
'date' (YYYY-MM-DD), 
'total_amount' (float), 
'currency' (ISO code), 
'category' (guess based on items: Groceries, Dining Out, Transport, etc.), 
and 'description' (shop name). 
If the currency is not EUR, return 'UNKNOWN' for the currency field.
Return ONLY the raw JSON string, no markdown formatting.
"""
