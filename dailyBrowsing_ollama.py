#!/usr/bin/env python3
"""
Browsing Digest Summarizer (Windows-Ready Edition)

Generates a 2-minute digest of your daily browsing using a local LLM.
Works 100% offline with Ollama. Automatically repairs malformed JSON files.

Usage:
    python summarize.py browsing-digest-2025-01-19.json
    python summarize.py browsing-digest-2025-01-19.json --model llama3.2
    python summarize.py browsing-digest-2025-01-19.json --output my-digest.md
"""

import json
import sys
import argparse
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


def normalize_json_keys(obj: Any) -> Any:
    """
    Recursively normalize JSON keys and string values by stripping whitespace.
    
    Fixes common export issues where keys/values contain trailing spaces like:
        "date ": "2026-02-06 "  →  "date": "2026-02-06"
    
    Args:
        obj: JSON object (dict, list, str, or primitive)
    
    Returns:
        Normalized object with cleaned keys/values
    """
    if isinstance(obj, dict):
        return {
            key.strip(): normalize_json_keys(value)
            for key, value in obj.items()
            if key.strip()  # Skip empty keys after stripping
        }
    elif isinstance(obj, list):
        return [normalize_json_keys(item) for item in obj]
    elif isinstance(obj, str):
        return obj.strip()
    else:
        return obj


def check_ollama() -> bool:
    """Check if Ollama is running."""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=5,
            encoding='utf-8',
            errors='replace'
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def get_available_models() -> list[str]:
    """Get list of available Ollama models."""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10,
            encoding='utf-8',
            errors='replace'
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            models = [line.split()[0] for line in lines if line.strip()]
            return models
        return []
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


def call_ollama(prompt: str, model: str = "llama3.2") -> str:
    """
    Call Ollama with a prompt and return the response.
    
    Uses UTF-8 encoding explicitly to handle Unicode characters on Windows.
    
    Args:
        prompt: Text prompt to send to the model
        model: Ollama model name to use
    
    Returns:
        Model's response text
    
    Raises:
        RuntimeError: If Ollama fails or times out
    """
    try:
        result = subprocess.run(
            ["ollama", "run", model],
            input=prompt,
            capture_output=True,
            text=True,
            encoding='utf-8',      # Critical for Windows Unicode support
            errors='replace',      # Safely handle unencodable characters
            timeout=120            # 2 minute timeout
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Ollama error: {result.stderr.strip()}")
        
        return result.stdout.strip()
    
    except subprocess.TimeoutExpired:
        raise RuntimeError("Ollama timed out. The model might be too slow or the input too large.")
    except FileNotFoundError:
        raise RuntimeError("Ollama not found. Please install it from https://ollama.ai")


def load_browsing_data(filepath: str) -> dict:
    """
    Load and repair browsing data from JSON file.
    
    Automatically fixes common export issues:
    - Keys with trailing/leading spaces ("date " → "date")
    - Values with trailing spaces ("2026-02-06 " → "2026-02-06")
    - Preserves backup of original file if repairs were needed
    
    Args:
        filepath: Path to JSON file
    
    Returns:
        Normalized browsing data dictionary
    
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file isn't valid JSON or lacks required structure
    """
    path = Path(filepath)
    
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    
    if not path.suffix.lower() == '.json':
        raise ValueError(f"Expected JSON file, got: {path.suffix}")
    
    # Load raw JSON content
    try:
        with open(path, 'r', encoding='utf-8') as f:
            raw_content = f.read()
            data = json.loads(raw_content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {e}")
    
    # Check if repair is needed (detect whitespace in keys)
    needs_repair = any(
        isinstance(k, str) and (k.startswith(' ') or k.endswith(' '))
        for k in _collect_keys(data)
    )
    
    if needs_repair:
        print(f"⚠️  Malformed JSON detected - repairing keys/values...")
        original_backup = path.with_suffix('.json.bak')
        shutil.copy2(path, original_backup)
        print(f"   Original saved as: {original_backup.name}")
        
        # Repair the data structure
        repaired_data = normalize_json_keys(data)
        
        # Save repaired version
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(repaired_data, f, indent=2, ensure_ascii=False)
        print(f"   Repaired JSON saved to: {path.name}")
        data = repaired_data
    
    # Validate required structure
    required_keys = {'date', 'pages'}
    actual_keys = set(data.keys())
    missing_keys = required_keys - actual_keys
    
    if missing_keys:
        raise ValueError(
            f"JSON missing required keys: {missing_keys}. "
            f"Found keys: {actual_keys}. "
            "This may indicate a severely malformed export file."
        )
    
    return data


def _collect_keys(obj: Any, keys: set = None) -> set:
    """Helper to collect all keys from nested JSON structures."""
    if keys is None:
        keys = set()
    
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str):
                keys.add(k)
            _collect_keys(v, keys)
    elif isinstance(obj, list):
        for item in obj:
            _collect_keys(item, keys)
    
    return keys


def prepare_content_for_llm(data: dict, max_tokens: int = 4000) -> str:
    """Prepare browsing content for LLM summarization."""
    pages = data.get('pages', [])
    
    if not pages:
        return ""
    
    # Sort by timestamp
    pages = sorted(pages, key=lambda x: x.get('timestamp', ''))
    
    # Build content string with budget
    content_parts = []
    estimated_tokens = 0
    tokens_per_char = 0.25  # Rough estimate
    
    for page in pages:
        title = page.get('title', 'Untitled')
        domain = page.get('domain', 'Unknown')
        content = page.get('content', '')[:1000]  # Limit per-page content
        timestamp = page.get('timestamp', '')
        
        # Format time
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            time_str = dt.strftime('%H:%M')
        except (ValueError, AttributeError):
            time_str = 'Unknown time'
        
        page_text = f"""
---
[{time_str}] {title}
Source: {domain}
Content: {content}
"""
        
        page_tokens = len(page_text) * tokens_per_char
        
        if estimated_tokens + page_tokens > max_tokens:
            break
        
        content_parts.append(page_text)
        estimated_tokens += page_tokens
    
    return "\n".join(content_parts)


def generate_summary(content: str, model: str, date: str) -> str:
    """Generate a summary using the local LLM."""
    
    prompt = f"""You are a personal assistant that creates concise daily browsing digests.

Below is a log of web pages I visited on {date}. Please create a 2-minute reading digest that:

1. **Main Themes**: What topics did I spend time on today? (2-3 bullet points)
2. **Key Insights**: What are the most important things I learned? (3-5 bullet points)
3. **Action Items**: Any tasks, ideas, or follow-ups worth noting? (if applicable)
4. **Time Analysis**: Brief observation about my browsing patterns

Keep it conversational and useful. Skip the fluff.

---
BROWSING LOG:
{content}
---

Now write my digest:"""

    return call_ollama(prompt, model)


def save_digest(digest: str, output_path: str, date: str, stats: dict):
    """Save the digest to a markdown file."""
    
    full_content = f"""# 📚 Browsing Digest - {date}

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Pages analyzed**: {stats['total_pages']}
**Estimated reading time**: {stats['total_reading_time']} minutes

---

{digest}

---

*Generated locally using Ollama. No data left your machine.*
"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(full_content)


def main():
    parser = argparse.ArgumentParser(
        description="Generate a 2-minute digest of your daily browsing using local AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python summarize.py browsing-digest-2025-01-19.json
    python summarize.py data.json --model mistral
    python summarize.py data.json --output today.md
        """
    )
    
    parser.add_argument(
        "input_file",
        help="JSON file exported from Browsing Digest extension"
    )
    
    parser.add_argument(
        "--model", "-m",
        default="llama3.2",
        help="Ollama model to use (default: llama3.2)"
    )
    
    parser.add_argument(
        "--output", "-o",
        help="Output markdown file (default: digest-YYYY-MM-DD.md)"
    )
    
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List available Ollama models and exit"
    )
    
    args = parser.parse_args()
    
    # List models if requested
    if args.list_models:
        print("Available Ollama models:")
        models = get_available_models()
        if models:
            for model in models:
                print(f"  - {model}")
        else:
            print("  No models found. Run: ollama pull llama3.2")
        sys.exit(0)
    
    # Check Ollama
    print("🔍 Checking Ollama...")
    if not check_ollama():
        print("❌ Ollama is not running!")
        print("   Start it with: ollama serve")
        print("   Or install from: https://ollama.ai")
        sys.exit(1)
    print("✅ Ollama is running")
    
    # Check model availability
    available_models = get_available_models()
    if args.model not in available_models and not any(args.model in m for m in available_models):
        print(f"⚠️  Model '{args.model}' not found locally")
        print(f"   Pulling model... (this may take a while)")
        subprocess.run(
            ["ollama", "pull", args.model],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
    
    # Load and repair data
    print(f"📂 Loading {args.input_file}...")
    try:
        data = load_browsing_data(args.input_file)
    except (FileNotFoundError, ValueError) as e:
        print(f"❌ Error loading file: {e}")
        sys.exit(1)
    
    # Check if there's data
    pages = data.get('pages', [])
    if not pages:
        print("❌ No browsing data found in the file")
        sys.exit(1)
    
    date = data.get('date', 'Unknown date')
    total_pages = data.get('totalPages', len(pages))
    total_reading_time = sum(p.get('readingTime', 0) for p in pages)
    
    print(f"📊 Found {total_pages} pages ({total_reading_time} min reading time)")
    
    # Prepare content
    print("📝 Preparing content for summarization...")
    content = prepare_content_for_llm(data)
    
    if not content:
        print("❌ No content to summarize")
        sys.exit(1)
    
    # Generate summary
    print(f"🤖 Generating digest with {args.model}...")
    print("   (This may take 30-60 seconds)")
    
    try:
        digest = generate_summary(content, args.model, date)
    except RuntimeError as e:
        print(f"❌ Error generating summary: {e}")
        sys.exit(1)
    
    # Determine output path
    if args.output:
        output_path = args.output
    else:
        # Sanitize date for filename (remove invalid characters)
        safe_date = "".join(c if c.isalnum() else "-" for c in str(date))
        output_path = f"digest-{safe_date}.md"
    
    # Save digest
    print(f"💾 Saving to {output_path}...")
    save_digest(
        digest, 
        output_path, 
        date,
        {'total_pages': total_pages, 'total_reading_time': total_reading_time}
    )
    
    print(f"✅ Done! Your digest is ready: {output_path}")
    print("\n" + "=" * 50)
    print("PREVIEW:")
    print("=" * 50)
    preview = digest[:500] + "..." if len(digest) > 500 else digest
    # Ensure preview prints correctly on Windows
    print(preview.encode('utf-8', errors='replace').decode('utf-8', errors='replace'))


if __name__ == "__main__":
    main()