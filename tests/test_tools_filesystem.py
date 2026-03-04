"""Tests for filesystem tools (Read, Write)."""

from pathlib import Path
from bladerunner.tools.filesystem import ReadTool, WriteTool


def test_read_tool_reads_file_content(tmp_path: Path) -> None:
    """ReadTool should read file content correctly."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello, World!")
    
    tool = ReadTool()
    result = tool.execute(file_path=str(test_file))
    
    assert result == "Hello, World!"


def test_read_tool_handles_file_not_found(tmp_path: Path) -> None:
    """ReadTool should handle missing files gracefully."""
    tool = ReadTool()
    result = tool.execute(file_path=str(tmp_path / "nonexistent.txt"))
    
    assert "Error: File" in result
    assert "not found" in result


def test_read_tool_handles_permission_error(tmp_path: Path) -> None:
    """ReadTool should handle permission errors."""
    import os
    
    test_file = tmp_path / "locked.txt"
    test_file.write_text("content")
    
    # Make file unreadable (Unix only)
    if os.name != 'nt':
        os.chmod(test_file, 0o000)
        
        tool = ReadTool()
        result = tool.execute(file_path=str(test_file))
        
        assert "Error:" in result
        assert "Permission denied" in result or "Error reading file" in result
        
        # Restore permissions for cleanup
        os.chmod(test_file, 0o644)


def test_read_tool_handles_utf8_encoding(tmp_path: Path) -> None:
    """ReadTool should handle UTF-8 encoded files."""
    test_file = tmp_path / "unicode.txt"
    test_file.write_text("Hello 世界 🌍", encoding="utf-8")
    
    tool = ReadTool()
    result = tool.execute(file_path=str(test_file))
    
    assert result == "Hello 世界 🌍"


def test_write_tool_writes_file_content(tmp_path: Path) -> None:
    """WriteTool should write file content correctly."""
    test_file = tmp_path / "output.txt"
    
    tool = WriteTool()
    result = tool.execute(file_path=str(test_file), content="Test content")
    
    assert "Successfully wrote" in result
    assert test_file.read_text() == "Test content"


def test_write_tool_creates_directories(tmp_path: Path) -> None:
    """WriteTool should create parent directories if needed."""
    nested_file = tmp_path / "nested" / "dir" / "file.txt"
    
    tool = WriteTool()
    result = tool.execute(file_path=str(nested_file), content="Nested content")
    
    assert "Successfully wrote" in result
    assert nested_file.exists()
    assert nested_file.read_text() == "Nested content"


def test_write_tool_overwrites_existing_file(tmp_path: Path) -> None:
    """WriteTool should overwrite existing files."""
    test_file = tmp_path / "existing.txt"
    test_file.write_text("Old content")
    
    tool = WriteTool()
    result = tool.execute(file_path=str(test_file), content="New content")
    
    assert "Successfully wrote" in result
    assert test_file.read_text() == "New content"


def test_write_tool_handles_utf8_encoding(tmp_path: Path) -> None:
    """WriteTool should handle UTF-8 encoding."""
    test_file = tmp_path / "unicode_out.txt"
    
    tool = WriteTool()
    result = tool.execute(file_path=str(test_file), content="Unicode: 日本語 ñ")
    
    assert "Successfully wrote" in result
    assert test_file.read_text(encoding="utf-8") == "Unicode: 日本語 ñ"


def test_write_tool_handles_permission_error(tmp_path: Path) -> None:
    """WriteTool should handle permission errors."""
    import os
    
    if os.name != 'nt':
        # Make directory read-only
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        os.chmod(readonly_dir, 0o444)
        
        tool = WriteTool()
        result = tool.execute(
            file_path=str(readonly_dir / "file.txt"),
            content="content"
        )
        
        assert "Error:" in result
        assert "Permission denied" in result or "Error writing file" in result
        
        # Restore permissions for cleanup
        os.chmod(readonly_dir, 0o755)


def test_read_tool_definition() -> None:
    """ReadTool should have proper definition."""
    tool = ReadTool()
    
    assert tool.name == "Read"
    assert "read" in tool.description.lower()
    assert "file_path" in tool.parameters["properties"]
    assert tool.parameters["required"] == ["file_path"]


def test_write_tool_definition() -> None:
    """WriteTool should have proper definition."""
    tool = WriteTool()
    
    assert tool.name == "Write"
    assert "write" in tool.description.lower()
    assert "file_path" in tool.parameters["properties"]
    assert "content" in tool.parameters["properties"]
    assert set(tool.parameters["required"]) == {"file_path", "content"}
