import io
import os
import pytest
from app.services.receipt_service import ReceiptService

TEST_UPLOAD_DIR = ReceiptService.UPLOAD_DIR

@pytest.fixture(autouse=True)
def cleanup_upload_dir(tmp_path, monkeypatch):
    # Redirect upload dir to a tmp path for tests
    monkeypatch.setattr(ReceiptService, 'UPLOAD_DIR', str(tmp_path))
    os.makedirs(ReceiptService.UPLOAD_DIR, exist_ok=True)
    yield
    # cleanup handled by tmp_path

def read_fixture(name):
    path = os.path.join(os.path.dirname(__file__), 'test_receipts', name)
    with open(path, 'rb') as f:
        return f.read()

@pytest.mark.parametrize('bad_bytes', [b'notanimage', b'<html></html>'])
def test_invalid_upload_rejected(bad_bytes):
    with pytest.raises(ValueError):
        # pass raw bytes directly
        pytest.run(asyncio=None) if False else None
        # call async function via asyncio.run
        import asyncio
        asyncio.run(ReceiptService.process_receipt(bad_bytes, 'test.txt'))

def test_valid_jpeg_saved():
    img_bytes = read_fixture('test.jpg')
    import asyncio
    result, path = asyncio.run(ReceiptService.process_receipt(io.BytesIO(img_bytes), 'test.jpg'))
    assert os.path.exists(path)
    assert path.endswith('.jpg') or path.endswith('.jpeg')

def test_safe_filename_blocks_traversal():
    img_bytes = read_fixture('test.jpg')
    import asyncio
    result, path = asyncio.run(ReceiptService.process_receipt(io.BytesIO(img_bytes), '../evil.jpg'))
    assert os.path.exists(path)
    assert '..' not in os.path.basename(path)
