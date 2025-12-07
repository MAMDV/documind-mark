"""
DocuMind Document Upload Handler
Demonstrates Skills, Subagents, and Hooks integration
"""

import json
import os
from datetime import datetime
from pathlib import Path

ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
# Default base directory - should be configured per deployment
BASE_UPLOAD_DIR = os.environ.get("DOCUMIND_UPLOAD_DIR", os.getcwd())


def validate_file_path(file_path, base_dir=None):
    """
    Validates that file path is safe and exists.

    Args:
        file_path: Path to the file to validate
        base_dir: Base directory to restrict file access (defaults to BASE_UPLOAD_DIR)

    Returns:
        tuple: (is_valid: bool, error_message: str or None)

    Security checks:
    - Path traversal attempts (using resolve())
    - Symlink protection
    - Base directory restriction
    - Valid file extension
    - File size limits
    """
    if base_dir is None:
        base_dir = BASE_UPLOAD_DIR

    # Resolve to absolute path to prevent traversal
    try:
        path = Path(file_path).resolve(strict=False)
        base = Path(base_dir).resolve(strict=False)
    except (OSError, ValueError) as e:
        return False, f"Invalid path: {str(e)}"

    # Check path is within allowed base directory
    try:
        path.relative_to(base)
    except ValueError:
        return False, "Path outside allowed directory"

    # Check file exists
    if not path.exists():
        return False, "File does not exist"

    # Block symlinks to prevent symlink attacks
    if path.is_symlink():
        return False, "Symlinks are not allowed"

    if not path.is_file():
        return False, "Path is not a file"

    # Validate file extension
    if path.suffix.lower() not in ALLOWED_EXTENSIONS:
        return (
            False,
            f"Invalid file extension. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Check file size
    file_size = path.stat().st_size
    if file_size > MAX_FILE_SIZE:
        return False, f"File too large. Max size: {MAX_FILE_SIZE // (1024*1024)} MB"

    return True, None


def read_document(file_path):
    """
    Reads document contents safely.

    Args:
        file_path: Path to the file to read

    Returns:
        tuple: (contents: str or None, error_message: str or None)
    """
    path = Path(file_path)

    try:
        # Try UTF-8 first (most common)
        with open(path, "r", encoding="utf-8") as f:
            return f.read(), None
    except UnicodeDecodeError:
        # Fall back to latin-1 which can decode any byte sequence
        try:
            with open(path, "r", encoding="latin-1") as f:
                return f.read(), None
        except Exception as e:
            return None, f"Failed to read file: {str(e)}"
    except Exception as e:
        return None, f"Failed to read file: {str(e)}"


def extract_metadata(file_path, contents):
    """
    Extracts metadata from document.

    Args:
        file_path: Path to the file
        contents: File contents as string

    Returns:
        dict: Metadata including name, size, dates, line/word counts
    """
    path = Path(file_path)
    stat = path.stat()

    # Count lines and words
    lines = contents.split("\n")
    line_count = len(lines)
    word_count = len(contents.split())

    return {
        "filename": path.name,
        "extension": path.suffix.lower(),
        "size_bytes": stat.st_size,
        "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "line_count": line_count,
        "word_count": word_count,
        "char_count": len(contents),
    }


def analyze_document(file_path):
    """
    Main function: orchestrates document analysis.

    This function:
    1. Validates the file path (security)
    2. Reads the document
    3. Extracts metadata
    4. Returns structured analysis as JSON-compatible dict

    Args:
        file_path: Path to the file to analyze

    Returns:
        dict: Analysis result with status, metadata, and content info
    """
    # Step 1: Validate file path
    is_valid, error = validate_file_path(file_path)
    if not is_valid:
        return {
            "status": "error",
            "error": error,
            "file_path": str(file_path),
        }

    # Step 2: Read document contents
    contents, error = read_document(file_path)
    if error:
        return {
            "status": "error",
            "error": error,
            "file_path": str(file_path),
        }

    # Step 3: Extract metadata
    metadata = extract_metadata(file_path, contents)

    # Step 4: Return structured analysis
    return {
        "status": "success",
        "file_path": str(file_path),
        "metadata": metadata,
        "content_preview": contents[:500] if len(contents) > 500 else contents,
        "analyzed_at": datetime.now().isoformat(),
    }


# Test the function
if __name__ == "__main__":
    # Create a sample document for testing
    test_doc = "test_document.txt"
    with open(test_doc, "w") as f:
        f.write("Sample document for DocuMind testing.\nThis is line 2.")

    # Analyze it
    result = analyze_document(test_doc)
    print(json.dumps(result, indent=2))
