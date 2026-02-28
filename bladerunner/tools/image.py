"""Image handling tools."""

import base64
import io
from pathlib import Path
from typing import Any, Dict, Optional
from .base import Tool

try:
    from PIL import Image

    IMAGE_AVAILABLE = True
except ImportError:
    IMAGE_AVAILABLE = False


class ImageHandler:
    """Handles image encoding and processing."""

    @staticmethod
    def encode_image(image_path: Path) -> Optional[Dict[str, Any]]:
        """Encode image to base64 with optimization."""
        if not IMAGE_AVAILABLE:
            return None

        try:
            img = Image.open(image_path)

            # Optimize: resize if too large (max 1568px on longest side)
            max_size = 1568
            if max(img.size) > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

            # Convert to bytes
            buffer = io.BytesIO()
            img_format = img.format or "PNG"
            img.save(buffer, format=img_format)
            img_bytes = buffer.getvalue()

            # Base64 encode
            b64_string = base64.b64encode(img_bytes).decode("utf-8")

            media_type = f"image/{img_format.lower()}"

            return {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": b64_string,
                },
            }
        except Exception:
            return None

    @staticmethod
    def is_image_path(path: str) -> bool:
        """Check if path is an image file."""
        return Path(path).suffix.lower() in {".jpg", ".jpeg", ".png", ".gif", ".webp"}


class ReadImageTool(Tool):
    """Read and analyze an image file."""

    @property
    def name(self) -> str:
        return "ReadImage"

    @property
    def description(self) -> str:
        return "Read and analyze an image file. Returns the image data for AI analysis."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["image_path"],
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "Path to the image file",
                }
            },
        }

    def execute(self, image_path: str) -> str:
        """Read image file."""
        if not IMAGE_AVAILABLE:
            return "Error: Image support requires 'Pillow' package"

        path = Path(image_path)
        if not path.exists():
            return f"Error: Image file '{image_path}' not found"

        if not ImageHandler.is_image_path(image_path):
            return f"Error: '{image_path}' is not a supported image format"

        # Image will be handled separately in agent loop
        return f"Image loaded from {image_path}"
