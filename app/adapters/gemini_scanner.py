import google.generativeai as genai
import PIL.Image
from app.interfaces.scanner import ReceiptScanner
from app.schemas.expense import ExpenseCreate
from app.core.config import settings
from app.core.prompts import RECEIPT_ANALYSIS_PROMPT
from app.utils.ai_parsing import parse_ai_response

class GeminiScanner(ReceiptScanner):
    def __init__(self):
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        # Using gemini-1.5-flash for speed and efficiency with images
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def scan_receipt(self, image_path: str) -> ExpenseCreate:
        img = PIL.Image.open(image_path)

        response = self.model.generate_content([RECEIPT_ANALYSIS_PROMPT, img])
        
        return parse_ai_response(response.text, image_path)
