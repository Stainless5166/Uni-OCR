import ipaddress
import os
import socket
import tempfile
import urllib.request
import urllib.parse
import base64
from pathlib import Path
from typing import List, Union
import fitz  # PyMuPDF

_ALLOWED_URL_SCHEMES = {"http", "https"}


def _is_public_address(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    return not (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_unspecified
    )


class InputProcessor:
    """Handles various input formats and converts them into image files for OCR engines."""
    
    def __init__(self):
        # Create a temporary directory that lives as long as the processor
        self.temp_dir = tempfile.TemporaryDirectory()
    
    def process(self, input_source: Union[str, Path]) -> List[Path]:
        """
        Process the input source and return a list of image paths.
        If the input is an image, it returns [image_path].
        If the input is a PDF, it returns a list of image paths (one per page).
        """
        source_str = str(input_source)
        local_path = None
        
        # 1. Handle URL
        if source_str.startswith("http://") or source_str.startswith("https://"):
            local_path = self._download_url(source_str)
        # 2. Handle Base64 (Assuming format like "data:image/png;base64,...")
        elif source_str.startswith("data:image") or source_str.startswith("data:application/pdf"):
            local_path = self._decode_base64(source_str)
        # 3. Local file
        else:
            local_path = Path(input_source)
            if not local_path.exists():
                raise FileNotFoundError(f"Input file not found: {local_path}")
        
        # Now we have a local_path, check if it's a PDF
        if local_path.suffix.lower() == '.pdf' or self._is_pdf(local_path):
            return self._flatten_pdf(local_path)
        
        # Assume it's already an image
        return [local_path]

    def _download_url(self, url: str) -> Path:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in _ALLOWED_URL_SCHEMES:
            raise ValueError(f"Unsupported URL scheme: {parsed.scheme!r}")
        if not parsed.hostname:
            raise ValueError("URL is missing a hostname")
        self._reject_non_public_host(parsed.hostname)

        # Determine extension from URL
        ext = Path(parsed.path).suffix or '.tmp'
        dest = Path(self.temp_dir.name) / f"downloaded{ext}"
        urllib.request.urlretrieve(url, dest)  # nosec B310 - scheme and host validated above
        return dest

    def _reject_non_public_host(self, hostname: str) -> None:
        """Block SSRF to loopback/private/link-local/metadata-style addresses.

        Resolves the hostname ourselves rather than trusting urlretrieve to
        land somewhere safe, since internal services (including the Docker
        bridge gateway and cloud metadata endpoints) are otherwise reachable
        from inside the container.
        """
        try:
            resolved = {info[4][0] for info in socket.getaddrinfo(hostname, None)}
        except socket.gaierror as exc:
            raise ValueError(f"Could not resolve host: {hostname}") from exc

        for ip in resolved:
            if not _is_public_address(ip):
                raise ValueError(
                    f"Refusing to fetch URL: {hostname!r} resolves to a non-public address ({ip})"
                )

    def _decode_base64(self, b64_str: str) -> Path:
        header, encoded = b64_str.split(",", 1)
        # Extract extension from header (e.g., data:image/png;base64)
        ext = '.png'
        if 'pdf' in header.lower():
            ext = '.pdf'
        elif 'jpeg' in header.lower() or 'jpg' in header.lower():
            ext = '.jpg'
            
        dest = Path(self.temp_dir.name) / f"decoded{ext}"
        with open(dest, "wb") as f:
            f.write(base64.b64decode(encoded))
        return dest

    def _is_pdf(self, path: Path) -> bool:
        with open(path, "rb") as f:
            header = f.read(4)
            return header == b"%PDF"

    def _flatten_pdf(self, pdf_path: Path) -> List[Path]:
        """Convert a PDF into a series of images using PyMuPDF."""
        doc = fitz.open(pdf_path)
        image_paths = []
        for i, page in enumerate(doc):
            pix = page.get_pixmap(dpi=150)
            img_path = Path(self.temp_dir.name) / f"page_{i}.png"
            pix.save(str(img_path))
            image_paths.append(img_path)
        return image_paths

    def cleanup(self):
        """Clean up temporary files."""
        self.temp_dir.cleanup()

