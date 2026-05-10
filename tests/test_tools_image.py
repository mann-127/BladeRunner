"""Tests for image handling tools."""

from bladerunner.tools.image import (
    IMAGE_AVAILABLE,
    ImageHandler,
    ReadImageTool,
)


def test_image_dependencies_available():
    """Image tools dependencies should be available."""
    assert IMAGE_AVAILABLE is True


def test_image_handler_is_image_path():
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


def test_image_handler_is_image_path_case_insensitive():
    """ImageHandler should handle case-insensitive extensions."""
    assert ImageHandler.is_image_path("photo.JPG") is True
    assert ImageHandler.is_image_path("image.PNG") is True
    assert ImageHandler.is_image_path("pic.JPEG") is True


def test_read_image_tool_definition():
    """ReadImageTool should have proper definition."""
    tool = ReadImageTool()

    assert tool.name == "ReadImage"
    assert "image" in tool.description.lower()
    assert "image_path" in tool.parameters["properties"]
    assert tool.parameters["required"] == ["image_path"]


def test_read_image_tool_validates_file_exists(tmp_path):
    """ReadImageTool should check if file exists."""
    tool = ReadImageTool()
    result = tool.execute(image_path=str(tmp_path / "missing.png"))

    assert "Error" in result
    assert "not found" in result


def test_read_image_tool_validates_image_format(tmp_path):
    """ReadImageTool should validate image file format."""
    # Create non-image file
    text_file = tmp_path / "document.txt"
    text_file.write_text("not an image")

    tool = ReadImageTool()
    result = tool.execute(image_path=str(text_file))

    assert "Error" in result
    assert "not a supported image format" in result


def test_read_image_tool_loads_valid_image(tmp_path):
    """ReadImageTool should successfully load valid image files."""
    # Create dummy image file
    image_file = tmp_path / "test.png"
    image_file.write_bytes(b"dummy-png-data")

    tool = ReadImageTool()
    result = tool.execute(image_path=str(image_file))

    # Should indicate successful load
    assert "Image loaded" in result
    assert str(image_file) in result or "test.png" in result


def test_read_image_tool_handles_different_formats(tmp_path):
    """ReadImageTool should handle various image formats."""
    formats = ["jpg", "jpeg", "png", "gif", "webp"]

    for fmt in formats:
        image_file = tmp_path / f"test.{fmt}"
        image_file.write_bytes(b"dummy-data")

        tool = ReadImageTool()
        result = tool.execute(image_path=str(image_file))

        # Should process without format errors
        assert "not a supported image format" not in result


def test_read_image_tool_returns_path_info(tmp_path):
    """ReadImageTool should include path information in response."""
    image_file = tmp_path / "photo.jpg"
    image_file.write_bytes(b"dummy")

    tool = ReadImageTool()
    result = tool.execute(image_path=str(image_file))

    # Response should reference the image path
    assert "photo.jpg" in result or str(image_file) in result
