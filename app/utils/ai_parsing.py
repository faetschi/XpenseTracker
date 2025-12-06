import json
from decimal import Decimal
from datetime import datetime
from app.schemas.expense import ExpenseCreate

def parse_ai_response(raw_response: str, image_path: str) -> ExpenseCreate:
    """
    Parses the raw JSON string response from an AI provider and converts it into an ExpenseCreate schema.
    Handles markdown code block stripping and basic data conversion.
    """
    try:
        # Clean response text (remove markdown code blocks if present)
        json_str = raw_response.strip()
        if json_str.startswith("```json"):
            json_str = json_str[7:]
        elif json_str.startswith("```"):
            json_str = json_str[3:]
        
        if json_str.endswith("```"):
            json_str = json_str[:-3]
        
        data = json.loads(json_str)
        
        amount = Decimal(str(data.get('total_amount', 0)))
        # No conversion logic as per requirement
        exchange_rate = Decimal("1.0")
        amount_eur = amount

        return ExpenseCreate(
            date=datetime.strptime(data['date'], '%d.%m.%Y').date(),
            category=data['category'],
            description=data['description'],
            amount=amount,
            currency=data['currency'],
            amount_eur=amount_eur,
            exchange_rate=exchange_rate,
            receipt_image_path=image_path,
            is_verified=False
        )
    except Exception as e:
        print(f"Error parsing AI response: {e}")
        print(f"Raw response: {raw_response}")
        raise e
