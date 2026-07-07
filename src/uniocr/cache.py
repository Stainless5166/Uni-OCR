import hashlib
import tempfile
import logging
from pathlib import Path
from typing import Dict, List

from . import UniOCR
from .models import Document

logger = logging.getLogger(__name__)

class OcrCache:
    """In-memory LRU Cache for OCR Extraction Results to prevent redundant processing."""
    
    def __init__(self, maxsize: int = 10):
        self.maxsize = maxsize
        self.cache: Dict[str, Document] = {}
        self.keys: List[str] = []
        
    def get_or_extract(self, engine: str, content: bytes) -> Document:
        file_hash = hashlib.md5(content, usedforsecurity=False).hexdigest()
        cache_key = f"{engine}_{file_hash}"
        
        if cache_key in self.cache:
            logger.info(f"OCR Cache HIT for {cache_key}")
            return self.cache[cache_key]
            
        logger.info(f"OCR Cache MISS for {cache_key}. Extracting...")
        
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        tmp.write(content)
        tmp.close()
        
        in_path = Path(tmp.name)
        try:
            ocr = UniOCR(engine=engine)
            doc = ocr.extract(in_path)
        finally:
            in_path.unlink(missing_ok=True)
            
        self.cache[cache_key] = doc
        self.keys.append(cache_key)
        
        if len(self.keys) > self.maxsize:
            oldest = self.keys.pop(0)
            self.cache.pop(oldest, None)
            
        return doc

ocr_cache = OcrCache(maxsize=10)
