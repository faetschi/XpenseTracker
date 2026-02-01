import os
from datetime import datetime
from PIL import Image
import pillow_heif
from app.services.llm_factory import LLMFactory
from app.core.config import settings
from app.utils.logger import get_logger
import io
import uuid
import asyncio

# Register HEIF opener
pillow_heif.register_heif_opener()

logger = get_logger(__name__)

class ReceiptService:
    UPLOAD_DIR = "app/data/uploads"
    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.heic', '.heif', '.webp'}

    @staticmethod
    def _safe_filename(original_name: str, ext: str) -> str:
        """Generate a safe filename using a timestamp and uuid; keep provided extension."""
        base = os.path.basename(original_name or '')
        # Remove dangerous characters
        safe_base = ''.join(c for c in base if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
        unique = f"{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"
        return f"receipt_{unique}{ext}"

    @staticmethod
    def _is_allowed_extension(ext: str) -> bool:
        return ext.lower() in ReceiptService.ALLOWED_EXTENSIONS

    @staticmethod
    def get_public_url(filename: str) -> str:
        """Return the public URL for a given uploaded file name."""
        return f"/uploads/{filename}"

    @staticmethod
    def cleanup_old_uploads():
        """Deletes files in UPLOAD_DIR older than the configured retention period."""
        try:
            if not os.path.exists(ReceiptService.UPLOAD_DIR):
                return

            retention_minutes = settings.UPLOAD_RETENTION_MINUTES
            now = datetime.now().timestamp()

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
    async def save_receipt(file_obj, original_filename: str = None) -> str:
        """Save a receipt image with validation/normalization and return the file path."""
        try:
            # Ensure uploads dir exists
            os.makedirs(ReceiptService.UPLOAD_DIR, exist_ok=True)

            # Cleanup old files in background to not block the request
            asyncio.create_task(asyncio.to_thread(ReceiptService.cleanup_old_uploads))

            # Extract content bytes
            content = None
            if hasattr(file_obj, 'read'):
                if hasattr(file_obj, 'seek'):
                    file_obj.seek(0)
                raw = file_obj.read()
                if hasattr(raw, '__await__'):
                    raw = await raw
                content = raw
            else:
                content = file_obj

            if content is None:
                logger.error("Upload content missing")
                raise ValueError("Upload content missing")

            # Validate image using PIL (this protects against non-image uploads)
            try:
                img = Image.open(io.BytesIO(content))
                img.verify()  # verify checks integrity
            except Exception as img_err:
                logger.error("Uploaded file is not a valid image", exc_info=True)
                raise ValueError("Uploaded file is not a valid image")

            # Decide on extension
            timestamp = int(datetime.now().timestamp())
            name_part = original_filename or 'unknown'
            _, ext = os.path.splitext(name_part)
            if not ext or not ReceiptService._is_allowed_extension(ext):
                # Default to .jpg
                ext = '.jpg'

            # Use safe filename
            filename = ReceiptService._safe_filename(name_part, ext)
            file_path = os.path.join(ReceiptService.UPLOAD_DIR, filename)
            logger.info(f"Saving receipt to {file_path} (original: {original_filename})")

            # Re-open image properly (note: verify() leaves file in an unusable state)
            image = Image.open(io.BytesIO(content)).convert('RGB')

            # Resize image to save RAM during processing
            try:
                max_size = settings.RECEIPT_MAX_SIZE_PX
                if image.width > max_size or image.height > max_size:
                    logger.info(f"Resizing image from {image.size} to max {max_size}px...")
                    image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            except Exception as resize_err:
                logger.warning(f"Image resizing failed: {resize_err}")

            # Normalize HEIC/HEIF or other formats to JPEG for consistent handling
            out_ext = ext.lower()
            if out_ext in ('.heic', '.heif'):
                out_ext = '.jpg'
                filename = os.path.splitext(filename)[0] + out_ext
                file_path = os.path.join(ReceiptService.UPLOAD_DIR, filename)

            # Save processed image (JPEG by default)
            try:
                save_kwargs = {}
                if out_ext in ('.jpg', '.jpeg'):
                    save_kwargs.update({'format': 'JPEG', 'quality': settings.RECEIPT_JPEG_QUALITY, 'optimize': True})
                image.save(file_path, **save_kwargs)
            except Exception as save_err:
                logger.error(f"Failed to save processed image: {save_err}", exc_info=True)
                raise

            return file_path

        except Exception:
            logger.error("Error processing receipt", exc_info=True)
            raise

    @staticmethod
    async def scan_receipt(file_path: str):
        """Run AI scan for a given file path."""
        logger.info("Starting AI scan...")
        scanner = LLMFactory.get_scanner()
        result = await asyncio.to_thread(scanner.scan_receipt, file_path)
        logger.debug(f"AI Scan result: {result}")
        return result

    @staticmethod
    async def process_receipt(file_obj, original_filename: str = None):
        """Backward-compatible wrapper: save + scan."""
        file_path = await ReceiptService.save_receipt(file_obj, original_filename)
        result = await ReceiptService.scan_receipt(file_path)
        return result, file_path
