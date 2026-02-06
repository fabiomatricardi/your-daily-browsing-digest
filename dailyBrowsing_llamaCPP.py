#!/usr/bin/env python3
"""
Browsing Digest Summarizer (llama.cpp Edition)

Generates a 2-minute digest of your daily browsing using a local LLM via llama.cpp server.
Works 100% offline with OpenAI-compatible API at http://localhost:8080/v1

Usage:
    python summarize.py browsing-digest-2025-01-19.json
    python summarize.py browsing-digest-2025-01-19.json --model local-model
    python summarize.py browsing-digest-2025-01-19.json --output my-digest.md
    python summarize.py --server http://localhost:8080/v1
"""

import json
import sys
import argparse
import requests
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from requests.exceptions import ConnectionError, Timeout, RequestException
from rich.console import Console
console = Console(width=90)
from rich.markdown import Markdown


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


def check_llama_cpp_server(server_url: str = "http://localhost:8080/v1") -> bool:
    """
    Check if llama.cpp server is running and responsive.
    
    Args:
        server_url: Base URL of the llama.cpp server API
    
    Returns:
        True if server is reachable and responding correctly
    """
    try:
        # Try health check endpoint first (llama.cpp specific)
        health_url = f"{server_url.rstrip('/').replace('/v1', '')}/health"
        response = requests.get(health_url, timeout=3)
        if response.status_code == 200:
            return True
        
        # Fallback to models endpoint (OpenAI-compatible)
        models_url = f"{server_url.rstrip('/')}/models"
        response = requests.get(models_url, timeout=3)
        return response.status_code == 200
    
    except (ConnectionError, Timeout, RequestException):
        return False


def call_llama_cpp_api(
    prompt: str,
    model: str = "local-model",
    server_url: str = "http://localhost:8080/v1",
    temperature: float = 0.7,
    max_tokens: int = 1500,
    timeout: int = 120
) -> str:
    """
    Call llama.cpp server via OpenAI-compatible API.
    
    Args:
        prompt: User prompt to send to the model
        model: Model identifier (usually "local-model" for llama.cpp)
        server_url: Base URL of the API server
        temperature: Sampling temperature (0.0-2.0)
        max_tokens: Maximum tokens to generate
        timeout: Request timeout in seconds
    
    Returns:
        Model's response text
    
    Raises:
        RuntimeError: If API call fails or returns error
    """
    api_endpoint = f"{server_url.rstrip('/')}/chat/completions"
    
    # Format as OpenAI chat completion request
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a personal assistant that creates concise daily browsing digests. "
                           "Keep responses focused, useful, and skip fluff."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False
    }
    
    try:
        response = requests.post(
            api_endpoint,
            json=payload,
            timeout=timeout,
            headers={"Content-Type": "application/json"}
        )
        
        # Handle HTTP errors
        if response.status_code != 200:
            error_detail = response.json().get("error", {}).get("message", response.text)
            raise RuntimeError(
                f"API error {response.status_code}: {error_detail[:200]}"
            )
        
        # Parse successful response
        result = response.json()
        if "choices" not in result or not result["choices"]:
            raise RuntimeError("Unexpected API response format: missing 'choices'")
        
        message = result["choices"][0].get("message", {})
        content = message.get("content", "").strip()
        
        if not content:
            raise RuntimeError("Received empty response from model")
        
        return content
    
    except (ConnectionError, Timeout) as e:
        raise RuntimeError(
            f"Connection failed to {server_url}. Is llama.cpp server running?\n"
            f"Start it with: ./server -c 4096 --port 8080\n"
            f"Error: {e}"
        )
    except RequestException as e:
        raise RuntimeError(f"API request failed: {e}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON response from API: {e}")


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


def generate_summary(
    content: str,
    model: str,
    date: str,
    server_url: str
) -> str:
    """Generate a summary using llama.cpp server via OpenAI-compatible API."""
    
    prompt = f"""Below is a log of web pages I visited on {date}. Create a 2-minute reading digest that:

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

    return call_llama_cpp_api(
        prompt=prompt,
        model=model,
        server_url=server_url,
        temperature=0.6,
        max_tokens=1200,
        timeout=180  # 3 minutes for larger contexts
    )


def save_digest(digest: str, output_path: str, date: str, stats: dict):
    """Save the digest to a markdown file."""
    
    full_content = f"""# 📚 Browsing Digest - {date}

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Pages analyzed**: {stats['total_pages']}
**Estimated reading time**: {stats['total_reading_time']} minutes

---

{digest}

---

*Generated locally using llama.cpp server. No data left your machine.*
"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(full_content)


def main():
    parser = argparse.ArgumentParser(
        description="Generate a 2-minute digest of your daily browsing using local AI (llama.cpp)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python summarize.py browsing-digest-2025-01-19.json
    python summarize.py data.json --model local-model
    python summarize.py data.json --server http://localhost:8080/v1
    python summarize.py data.json --output today.md

Requirements:
    - llama.cpp server running: ./server -c 4096 --port 8080
    - Install dependencies: pip install requests
        """
    )
    
    parser.add_argument(
        "input_file",
        help="JSON file exported from Browsing Digest extension"
    )
    
    parser.add_argument(
        "--model", "-m",
        default="local-model",
        help="Model identifier for API (default: local-model). "
             "Note: llama.cpp typically runs one model at a time."
    )
    
    parser.add_argument(
        "--server", "-s",
        default="http://localhost:8080/v1",
        help="llama.cpp server URL (default: http://localhost:8080/v1)"
    )
    
    parser.add_argument(
        "--output", "-o",
        help="Output markdown file (default: digest-YYYY-MM-DD.md)"
    )
    
    parser.add_argument(
        "--check-server",
        action="store_true",
        help="Check server status and exit"
    )
    
    args = parser.parse_args()
    
    # Server status check if requested
    if args.check_server:
        print(f"🔍 Checking llama.cpp server at {args.server}...")
        if check_llama_cpp_server(args.server):
            print("✅ Server is running and responsive")
            # Try to get model info
            try:
                resp = requests.get(f"{args.server.rstrip('/')}/models", timeout=5)
                if resp.status_code == 200:
                    models = resp.json().get("data", [])
                    if models:
                        print(f"📦 Loaded model: {models[0].get('id', 'unknown')}")
            except:
                pass
        else:
            print("❌ Server not reachable")
            print("   Start llama.cpp server with:")
            print("   ./server -c 4096 --port 8080")
        sys.exit(0)
    
    # Check server availability
    print(f"🔍 Checking llama.cpp server at {args.server}...")
    if not check_llama_cpp_server(args.server):
        print("❌ llama.cpp server is not running!")
        print(f"   Start it with: ./server -c 4096 --port 8080")
        print("   Or download from: https://github.com/ggerganov/llama.cpp")
        sys.exit(1)
    print("✅ Server is running")
    
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
    print(f"🤖 Generating digest with {args.model} via {args.server}...")
    print("   (This may take 30-90 seconds depending on context size)")
    
    try:
        digest = generate_summary(content, args.model, date, args.server)
    except RuntimeError as e:
        print(f"❌ Error generating summary: {e}")
        sys.exit(1)
    
    # Determine output path
    if args.output:
        output_path = args.output
    else:
        # Sanitize date for filename (remove invalid characters)
        safe_date = "".join(c if c.isalnum() or c in "-_" else "-" for c in str(date))
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
    console.print(Markdown(preview.encode('utf-8', errors='replace').decode('utf-8', errors='replace')))


if __name__ == "__main__":
    # Check for required dependency
    try:
        import requests
    except ImportError:
        print("❌ 'requests' library not found!")
        print("   Install it with: pip install requests")
        sys.exit(1)
    
    main()