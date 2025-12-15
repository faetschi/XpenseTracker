import base64
from openai import OpenAI
from app.interfaces.scanner import ReceiptScanner
from app.db.schemas import ExpenseCreate
from app.core.config import settings
from app.core.prompts import RECEIPT_ANALYSIS_PROMPT
from app.utils.ai_parsing import parse_ai_response

import mimetypes

class OpenAIScanner(ReceiptScanner):
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o" # Or gpt-4-turbo, capable of vision

    def _encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def scan_receipt(self, image_path: str) -> ExpenseCreate:
        base64_image = self._encode_image(image_path)
        
        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type:
            mime_type = "image/jpeg"

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": RECEIPT_ANALYSIS_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
            max_tokens=500,
        )

        content = response.choices[0].message.content
        return parse_ai_response(content, image_path)
