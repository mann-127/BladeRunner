"""Image handling tools."""

from pathlib import Path

from .base import Tool

try:
    from PIL import Image  # noqa: F401

    IMAGE_AVAILABLE = True
except ImportError:
    IMAGE_AVAILABLE = False


class ImageHandler:
    """Handles image encoding and processing."""

    @staticmethod
    def is_image_path(path):
        return Path(path).suffix.lower() in {".jpg", ".jpeg", ".png", ".gif", ".webp"}


class ReadImageTool(Tool):
    """Read and analyze an image file."""

    @property
    def name(self):
        return "ReadImage"

    @property
    def description(self):
        return "Read and analyze an image file. Returns the image data for AI analysis."

    @property
    def parameters(self):
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

    def execute(self, image_path):
        if not IMAGE_AVAILABLE:
            return "Error: Image support requires 'Pillow' package"

        path = Path(image_path)
        if not path.exists():
            return f"Error: Image file '{image_path}' not found"

        if not ImageHandler.is_image_path(image_path):
            return f"Error: '{image_path}' is not a supported image format"

        # Image will be handled separately in agent loop
        return f"Image loaded from {image_path}"
