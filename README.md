# your-daily-browsing-digest
summarize tour daily browsing activity locally with llama.cpp server and chrome extension


- original and inspiration article on Medium [here](https://medium.com/write-a-catalyst/i-made-an-ai-that-tells-me-what-i-actually-learned-online-each-day-001e1523693a)
- original GitHub repository [here](https://github.com/ManashWrites/I-Made-an-AI-That-Summarizes-My-Daily-Browsing-Into-a-2-Minute-Digest)

The original project by is an inspiration.

But it is not working out of the box on Windows (at least mine)
```repl
UnicodeEncodeError: 'charmap' codec can't encode character '\u200e' in position 1057: character maps to <undefined>
```

## My version
I refactored it with the following:

- working with Ollama on windows
- a version working with llama.cpp server running on localhost:8080

---

## 🔑 Key Features & Improvements

### ✅ llama.cpp Integration
- **OpenAI-compatible API**: Uses standard `/v1/chat/completions` endpoint
- **Robust error handling**: Detects connection issues, timeouts, and API errors
- **Health checks**: Verifies server status before processing
- **Flexible server URL**: Configurable via `--server` flag (default: `http://localhost:8080/v1`)

### ✅ Retained Critical Fixes
- **Automatic JSON repair**: Still fixes malformed keys/values with whitespace
- **Windows Unicode safety**: UTF-8 encoding throughout with error resilience
- **Backup preservation**: Creates `.json.bak` before modifying original files

### ✅ Optimized for llama.cpp
- **Single-model workflow**: Recognizes llama.cpp typically runs one model at a time
- **Larger timeout**: 180 seconds to handle bigger contexts (llama.cpp can be slower than Ollama)
- **Temperature control**: Set to 0.6 for more focused summaries
- **Health endpoint check**: Uses `/health` endpoint (llama.cpp specific) before falling back to `/models`

### ✅ Enhanced CLI Experience
```bash
# Basic usage (server must be running separately)
python dailyBrowsing_llamacpp.py browsing-digest-2026-02-06.json

# Check server status
python dailyBrowsing_llamacpp.py browsing-digest-2026-02-06.json --check-server

# Custom server URL
python dailyBrowsing_llamacpp.py browsing-digest-2026-02-06.json --server http://192.168.1.100:8080/v1

# Custom output filename
python dailyBrowsing_llamacpp.py browsing-digest-2026-02-06.json --output today-digest.md
```

### ⚙️ How to Run llama.cpp Server
```bash
# Download prebuilt server or build from source:
# https://github.com/ggerganov/llama.cpp

# Start server with your model (example):
./llama-server.exe -m models/llama-3-8b.Q4_K_M.gguf -c 4096 --port 8080

# Verify it's running:
curl http://localhost:8080/v1/models
```

### 📦 Requirements
```bash
pip install -r requirements.txt
```

This version gives you **full offline privacy** with the performance benefits of llama.cpp while maintaining all the robustness of your original tool. The API approach is also more stable than CLI piping (no more Unicode encoding issues on Windows!). 

