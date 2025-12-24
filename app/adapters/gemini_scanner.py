import google.genai as genai
import PIL.Image
from app.interfaces.scanner import ReceiptScanner
from app.db.schemas import ExpenseCreate
from app.core.config import settings
from app.core.prompts import RECEIPT_ANALYSIS_PROMPT
from app.utils.ai_parsing import parse_ai_response

class GeminiScanner(ReceiptScanner):
    def __init__(self):
        self.client = genai.Client(api_key=settings.GOOGLE_API_KEY)

    def scan_receipt(self, image_path: str) -> ExpenseCreate:
        img = PIL.Image.open(image_path)

        response = self.client.models.generate_content(
            model='gemini-1.5-flash',
            contents=[RECEIPT_ANALYSIS_PROMPT, img]
        )
        
        return parse_ai_response(response.text, image_path)
