"""
Comment loader module.

Supports loading comments from CSV, JSON (newline-delimited), and Parquet formats.
Converts raw data into domain Comment objects.
"""
import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import pandas as pd
except ImportError:
    pd = None

from ytce.ai.domain.comment import Comment
from ytce.ai.input.config import InputConfig


def load_comments(
    path: str,
    *,
    format: Optional[str] = None,
    id_field: Optional[str] = None,
    text_field: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[Comment]:
    """
    Load comments from a file (CSV, JSON, or Parquet).
    
    Automatically detects file format based on extension:
    - .csv -> CSV format
    - .json, .jsonl, .ndjson -> newline-delimited JSON
    - .parquet -> Parquet format
    
    Args:
        path: Path to the input file
        format: Optional format hint ("csv", "jsonl"/"json"/"ndjson", "parquet").
            If provided, it takes precedence over file extension detection.
        id_field: Optional field name for comment ID (overrides defaults).
        text_field: Optional field name for comment text (overrides defaults).
        
    Returns:
        List of Comment domain objects
        
    Raises:
        ValueError: If file format is not supported or file cannot be read
        FileNotFoundError: If file does not exist
    """
    file_path = Path(path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    fmt = (format or "").strip().lower()
    if fmt:
        if fmt in ("csv",):
            return _load_csv(path, id_field=id_field, text_field=text_field, limit=limit)
        if fmt in ("json", "jsonl", "ndjson"):
            return _load_json(path, id_field=id_field, text_field=text_field, limit=limit)
        if fmt in ("parquet",):
            return _load_parquet(path, id_field=id_field, text_field=text_field, limit=limit)
        raise ValueError(
            f"Unsupported format hint: {format}. Supported: csv, json/jsonl/ndjson, parquet"
        )

    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        return _load_csv(path, id_field=id_field, text_field=text_field, limit=limit)
    if suffix in (".json", ".jsonl", ".ndjson"):
        return _load_json(path, id_field=id_field, text_field=text_field, limit=limit)
    if suffix == ".parquet":
        return _load_parquet(path, id_field=id_field, text_field=text_field, limit=limit)
    raise ValueError(
        f"Unsupported file format: {suffix}. "
        "Supported formats: .csv, .json/.jsonl/.ndjson, .parquet"
    )


def load_comments_from_config(cfg: InputConfig, *, limit: Optional[int] = None) -> List[Comment]:
    """
    Load comments according to an InputConfig.

    This is the preferred entry point for the runner layer, because it respects
    the user-provided id_field/text_field mapping and explicit format.
    """
    return load_comments(
        cfg.path,
        format=cfg.format,
        id_field=cfg.id_field,
        text_field=cfg.text_field,
        limit=limit,
    )


def _load_csv(path: str, *, id_field: Optional[str], text_field: Optional[str], limit: Optional[int]) -> List[Comment]:
    """
    Load comments from CSV file.
    
    Expected CSV format:
    author,channel,cid,heart,photo,replies,reply,scraped_at,source,text,text_length,time,votes
    
    Args:
        path: Path to CSV file
        
    Returns:
        List of Comment objects
    """
    comments: List[Comment] = []
    
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        
        for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
            try:
                comment = _row_to_comment(
                    row,
                    source_format="csv",
                    id_field=id_field,
                    text_field=text_field,
                )
                comments.append(comment)
                if limit is not None and len(comments) >= limit:
                    break
            except (ValueError, KeyError) as e:
                raise ValueError(
                    f"Error parsing CSV row {row_num} in {path}: {e}"
                ) from e
    
    return comments


def _load_json(path: str, *, id_field: Optional[str], text_field: Optional[str], limit: Optional[int]) -> List[Comment]:
    """
    Load comments from newline-delimited JSON file (JSONL/NDJSON).
    
    Each line should be a valid JSON object with comment data.
    
    Args:
        path: Path to JSON/JSONL file
        
    Returns:
        List of Comment objects
    """
    comments: List[Comment] = []
    
    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:  # Skip empty lines
                continue
                
            try:
                data = json.loads(line)
                comment = _row_to_comment(
                    data,
                    source_format="json",
                    id_field=id_field,
                    text_field=text_field,
                )
                comments.append(comment)
                if limit is not None and len(comments) >= limit:
                    break
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Invalid JSON on line {line_num} in {path}: {e}"
                ) from e
            except (ValueError, KeyError) as e:
                raise ValueError(
                    f"Error parsing JSON line {line_num} in {path}: {e}"
                ) from e
    
    return comments


def _load_parquet(path: str, *, id_field: Optional[str], text_field: Optional[str], limit: Optional[int]) -> List[Comment]:
    """
    Load comments from Parquet file.
    
    Args:
        path: Path to Parquet file
        
    Returns:
        List of Comment objects
        
    Raises:
        ImportError: If pandas is not installed
    """
    if pd is None:
        raise ImportError(
            "pandas is required for Parquet support. "
            "Install it with: pip install pandas pyarrow"
        )
    
    try:
        df = pd.read_parquet(path)
    except Exception as e:
        raise ValueError(f"Error reading Parquet file {path}: {e}") from e

    if limit is not None:
        df = df.head(limit)
    
    comments: List[Comment] = []
    
    for idx, row in df.iterrows():
        try:
            # Convert pandas Series to dict, handling NaN values
            row_dict = {}
            for key, value in row.items():
                # Convert NaN/None values to None (pandas uses pd.NA, NaN, etc.)
                is_nan = False
                if pd is not None:
                    try:
                        is_nan = pd.isna(value)
                    except (TypeError, ValueError):
                        is_nan = value is None or (isinstance(value, float) and str(value).lower() == 'nan')
                else:
                    is_nan = value is None or (isinstance(value, float) and str(value).lower() == 'nan')
                
                row_dict[key] = None if is_nan else value
            
            comment = _row_to_comment(
                row_dict,
                source_format="parquet",
                id_field=id_field,
                text_field=text_field,
            )
            comments.append(comment)
        except (ValueError, KeyError) as e:
            raise ValueError(
                f"Error parsing Parquet row {idx} in {path}: {e}"
            ) from e
    
    return comments


def _row_to_comment(
    row: Dict[str, Any],
    source_format: str,
    *,
    id_field: Optional[str],
    text_field: Optional[str],
) -> Comment:
    """
    Convert a raw data row (from CSV/JSON/Parquet) into a Comment domain object.
    
    Handles different field name variations:
    - id/cid: comment identifier
    - text: comment text (required)
    - author: author name (optional)
    - channel: channel ID (optional)
    - votes: vote count (optional, can be string or int)
    
    Args:
        row: Dictionary with comment data
        source_format: Source format name for error messages
        
    Returns:
        Comment domain object
        
    Raises:
        ValueError: If required fields are missing or invalid
    """
    # Extract comment ID (prefer configured field, then common defaults)
    comment_id = row.get(id_field) if id_field else None
    comment_id = comment_id or row.get("cid") or row.get("id")
    if not comment_id:
        raise ValueError(
            f"Missing required comment ID field "
            f"({id_field!r} or 'cid'/'id') in {source_format} data"
        )
    # Handle None/NaN values (check for pandas NaN or Python None)
    if comment_id is None:
        raise ValueError(
            f"Field 'cid' or 'id' cannot be None in {source_format} data"
        )
    # Check for float NaN
    if isinstance(comment_id, float) and str(comment_id).lower() == 'nan':
        raise ValueError(
            f"Field 'cid' or 'id' cannot be NaN in {source_format} data"
        )
    if not isinstance(comment_id, str):
        comment_id = str(comment_id)
    # Ensure comment_id is not empty after conversion
    if not comment_id.strip():
        raise ValueError(
            f"Field 'cid' or 'id' cannot be empty in {source_format} data"
        )
    
    # Extract text (prefer configured field, then default 'text')
    text = row.get(text_field) if text_field else None
    text = text if text is not None else row.get("text")
    if text is None:
        raise ValueError(
            f"Missing required comment text field ({text_field!r} or 'text') in {source_format} data"
        )
    if not isinstance(text, str):
        text = str(text)
    # Ensure text is not empty
    if not text.strip():
        raise ValueError(f"Field 'text' cannot be empty in {source_format} data")
    
    # Extract optional metadata
    author = row.get("author")
    if author is not None:
        if not isinstance(author, str):
            author = str(author)
        # Convert empty strings to None
        author = author if author.strip() else None
    
    channel = row.get("channel")
    if channel is not None:
        if not isinstance(channel, str):
            channel = str(channel)
        # Convert empty strings to None
        channel = channel if channel.strip() else None
    
    # Extract votes (can be string or int)
    votes = row.get("votes")
    if votes is not None:
        if isinstance(votes, str):
            try:
                votes = int(votes) if votes.strip() else None
            except ValueError:
                votes = None
        elif not isinstance(votes, int):
            votes = None
    
    # Preserve all raw data for potential future use
    raw = dict(row)
    
    return Comment(
        id=comment_id,
        text=text,
        author=author,
        channel=channel,
        votes=votes,
        raw=raw,
    )


__all__ = ["load_comments", "load_comments_from_config"]

