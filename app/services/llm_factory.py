from app.interfaces.scanner import ReceiptScanner
from app.adapters.gemini_scanner import GeminiScanner
from app.adapters.openai_scanner import OpenAIScanner
from app.core.config import settings

class LLMFactory:
    @staticmethod
    def get_scanner() -> ReceiptScanner:
        provider = settings.AI_PROVIDER.lower()
        
        if provider == "openai":
            return OpenAIScanner()
        elif provider == "gemini":
            return GeminiScanner()
        else:
            # Default fallback
            return GeminiScanner()

