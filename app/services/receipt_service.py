import os
from datetime import datetime
from PIL import Image
import pillow_heif
from app.services.llm_factory import LLMFactory
from app.core.config import settings
from app.utils.logger import get_logger
import io
import asyncio

# Register HEIF opener
pillow_heif.register_heif_opener()

logger = get_logger(__name__)

class ReceiptService:
    UPLOAD_DIR = "app/data/uploads"

    @staticmethod
    def cleanup_old_uploads():
        """Deletes files in UPLOAD_DIR older than the configured retention period."""
        try:
            if not os.path.exists(ReceiptService.UPLOAD_DIR):
                return

            retention_minutes = settings.UPLOAD_RETENTION_MINUTES
            now = datetime.now().timestamp()
            
            # logger.debug(f"Checking for uploads older than {retention_minutes} minutes...")
            
            count = 0
            for filename in os.listdir(ReceiptService.UPLOAD_DIR):
                file_path = os.path.join(ReceiptService.UPLOAD_DIR, filename)
                if not os.path.isfile(file_path):
                    continue
                    
                file_mtime = os.path.getmtime(file_path)
                age_minutes = (now - file_mtime) / 60
                
                if age_minutes > retention_minutes:
                    try:
                        os.remove(file_path)
                        count += 1
                        logger.debug(f"Deleted old file: {filename}")
                    except Exception as e:
                        logger.warning(f"Failed to delete {filename}: {e}")
            
            if count > 0:
                logger.info(f"Cleanup complete. Deleted {count} files.")
                
        except Exception as e:
            logger.error(f"Error during upload cleanup: {e}")

    @staticmethod
    async def process_receipt(file_obj, original_filename: str = None):
        """
        Handles the full receipt processing pipeline:
        1. Saves the file with a unique name.
        2. Converts HEIC to JPG if necessary.
        3. Scans the image using the configured AI provider.
        
        Args:
            file_obj: The file-like object (bytes, BytesIO, or similar) containing the image data.
            original_filename: The original name of the file (optional).
            
        Returns:
            The result object from the AI scanner.
        """
        try:
            # Ensure uploads dir exists
            os.makedirs(ReceiptService.UPLOAD_DIR, exist_ok=True)
            
            # Cleanup old files
            ReceiptService.cleanup_old_uploads()
            
            # Generate unique filename
            timestamp = int(datetime.now().timestamp())
            name_part = original_filename or 'unknown'
            _, ext = os.path.splitext(name_part)
            if not ext:
                ext = ".jpg"
            
            filename = f"receipt_{timestamp}{ext}"
            file_path = os.path.join(ReceiptService.UPLOAD_DIR, filename)
            
            logger.info(f"Saving receipt to {file_path} (original: {original_filename})")
            
            # Write content to disk
            # Handle async read if necessary, though usually passed as BytesIO here
            content = file_obj
            if hasattr(file_obj, 'read'):
                if hasattr(file_obj, 'seek'):
                    file_obj.seek(0)
                content = file_obj.read()
                # If read() returned a coroutine (should be handled by caller, but safety check)
                if hasattr(content, '__await__'):
                    content = await content

            with open(file_path, "wb") as f:
                f.write(content)
            
            # Handle HEIC conversion
            if filename.lower().endswith(('.heic', '.heif')):
                logger.info("Detected HEIC/HEIF. Converting to JPG...")
                try:
                    img = Image.open(file_path)
                    new_path = os.path.splitext(file_path)[0] + ".jpg"
                    img.save(new_path, "JPEG")
                    file_path = new_path
                    logger.info(f"Converted to {file_path}")
                except Exception as heic_err:
                    logger.error(f"HEIC conversion failed: {heic_err}", exc_info=True)
                    # Continue with original file
            
            # Run AI Scan
            logger.info("Starting AI scan...")
            scanner = LLMFactory.get_scanner()
            
            # Run synchronous scanner in a separate thread to avoid blocking the event loop
            result = await asyncio.to_thread(scanner.scan_receipt, file_path)
            
            logger.debug(f"AI Scan result: {result}")
            
            return result, file_path

        except Exception as e:
            logger.error(f"Error processing receipt: {e}", exc_info=True)
            raise e
