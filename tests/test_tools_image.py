"""Tests for image handling tools."""

from pathlib import Path
from unittest.mock import Mock, patch
from bladerunner.tools.image import (
    ImageHandler,
    ReadImageTool,
    IMAGE_AVAILABLE,
)


def test_image_dependencies_available() -> None:
    """Image tools dependencies should be available."""
    assert IMAGE_AVAILABLE is True


def test_image_handler_is_image_path() -> None:
    """ImageHandler should correctly identify image file extensions."""
    assert ImageHandler.is_image_path("photo.jpg") is True
    assert ImageHandler.is_image_path("image.jpeg") is True
    assert ImageHandler.is_image_path("picture.png") is True
    assert ImageHandler.is_image_path("animation.gif") is True
    assert ImageHandler.is_image_path("photo.webp") is True

    # Non-image files
    assert ImageHandler.is_image_path("document.pdf") is False
    assert ImageHandler.is_image_path("script.py") is False
    assert ImageHandler.is_image_path("data.json") is False


def test_image_handler_is_image_path_case_insensitive() -> None:
    """ImageHandler should handle case-insensitive extensions."""
    assert ImageHandler.is_image_path("photo.JPG") is True
    assert ImageHandler.is_image_path("image.PNG") is True
    assert ImageHandler.is_image_path("pic.JPEG") is True


@patch("bladerunner.tools.image.Image.open")
def test_image_handler_encode_image_creates_base64(mock_open, tmp_path: Path) -> None:
    """ImageHandler should encode images to base64."""
    # Create a mock PIL Image
    mock_img = Mock()
    mock_img.size = (800, 600)
    mock_img.format = "PNG"

    def _save_side_effect(buf, format):
        buf.write(b"fake-image-data")

    mock_img.save = Mock(side_effect=_save_side_effect)
    mock_open.return_value = mock_img

    test_image = tmp_path / "test.png"
    test_image.write_bytes(b"dummy")

    result = ImageHandler.encode_image(test_image)

    assert result is not None
    assert result["type"] == "image"
    assert result["source"]["type"] == "base64"
    assert result["source"]["media_type"] == "image/png"
    assert "data" in result["source"]


@patch("bladerunner.tools.image.Image.open")
def test_image_handler_resizes_large_images(mock_open, tmp_path: Path) -> None:
    """ImageHandler should resize images that exceed max size."""
    mock_img = Mock()
    mock_img.size = (3000, 2000)  # Larger than 1568px max
    mock_img.format = "JPEG"
    mock_img.thumbnail = Mock()
    mock_img.save = Mock()
    mock_open.return_value = mock_img

    test_image = tmp_path / "large.jpg"
    test_image.write_bytes(b"dummy")

    ImageHandler.encode_image(test_image)

    # Should have called thumbnail to resize
    mock_img.thumbnail.assert_called_once()
    call_args = mock_img.thumbnail.call_args[0][0]
    assert call_args == (1568, 1568)


@patch("bladerunner.tools.image.Image.open")
def test_image_handler_preserves_small_images(
    mock_open, tmp_path: Path
) -> None:
    """ImageHandler should not resize images under max size."""
    mock_img = Mock()
    mock_img.size = (800, 600)  # Smaller than 1568px
    mock_img.format = "PNG"
    mock_img.thumbnail = Mock()
    mock_img.save = Mock()
    mock_open.return_value = mock_img

    test_image = tmp_path / "small.png"
    test_image.write_bytes(b"dummy")

    ImageHandler.encode_image(test_image)

    # Should NOT resize small images
    mock_img.thumbnail.assert_not_called()


@patch("bladerunner.tools.image.Image.open")
def test_image_handler_handles_format_detection(
    mock_open, tmp_path: Path
) -> None:
    """ImageHandler should detect image format correctly."""
    test_formats = [
        ("image.jpg", "JPEG", "image/jpeg"),
        ("image.png", "PNG", "image/png"),
        ("image.gif", "GIF", "image/gif"),
    ]

    for filename, pil_format, expected_media in test_formats:
        mock_img = Mock()
        mock_img.size = (100, 100)
        mock_img.format = pil_format
        mock_img.save = Mock()
        mock_open.return_value = mock_img

        test_image = tmp_path / filename
        test_image.write_bytes(b"dummy")

        result = ImageHandler.encode_image(test_image)
        assert result is not None
        assert result["source"]["media_type"] == expected_media


def test_image_handler_handles_errors_gracefully(tmp_path: Path) -> None:
    """ImageHandler should return None on errors."""
    # Non-existent file
    result = ImageHandler.encode_image(tmp_path / "nonexistent.png")
    assert result is None

    # Invalid image data
    bad_image = tmp_path / "corrupted.jpg"
    bad_image.write_bytes(b"not an image")
    result = ImageHandler.encode_image(bad_image)
    assert result is None


def test_read_image_tool_definition() -> None:
    """ReadImageTool should have proper definition."""
    tool = ReadImageTool()

    assert tool.name == "ReadImage"
    assert "image" in tool.description.lower()
    assert "image_path" in tool.parameters["properties"]
    assert tool.parameters["required"] == ["image_path"]


def test_read_image_tool_validates_file_exists(tmp_path: Path) -> None:
    """ReadImageTool should check if file exists."""
    tool = ReadImageTool()
    result = tool.execute(image_path=str(tmp_path / "missing.png"))

    assert "Error" in result
    assert "not found" in result


def test_read_image_tool_validates_image_format(tmp_path: Path) -> None:
    """ReadImageTool should validate image file format."""
    # Create non-image file
    text_file = tmp_path / "document.txt"
    text_file.write_text("not an image")

    tool = ReadImageTool()
    result = tool.execute(image_path=str(text_file))

    assert "Error" in result
    assert "not a supported image format" in result


def test_read_image_tool_loads_valid_image(tmp_path: Path) -> None:
    """ReadImageTool should successfully load valid image files."""
    # Create dummy image file
    image_file = tmp_path / "test.png"
    image_file.write_bytes(b"dummy-png-data")

    tool = ReadImageTool()
    result = tool.execute(image_path=str(image_file))

    # Should indicate successful load
    assert "Image loaded" in result
    assert str(image_file) in result or "test.png" in result


def test_read_image_tool_handles_different_formats(tmp_path: Path) -> None:
    """ReadImageTool should handle various image formats."""
    formats = ["jpg", "jpeg", "png", "gif", "webp"]

    for fmt in formats:
        image_file = tmp_path / f"test.{fmt}"
        image_file.write_bytes(b"dummy-data")

        tool = ReadImageTool()
        result = tool.execute(image_path=str(image_file))

        # Should process without format errors
        assert "not a supported image format" not in result


def test_read_image_tool_returns_path_info(tmp_path: Path) -> None:
    """ReadImageTool should include path information in response."""
    image_file = tmp_path / "photo.jpg"
    image_file.write_bytes(b"dummy")

    tool = ReadImageTool()
    result = tool.execute(image_path=str(image_file))

    # Response should reference the image path
    assert "photo.jpg" in result or str(image_file) in result
