# Your Daily browsing AI generated digest
summarize your daily browsing activity locally with llama.cpp server and chrome extension

<img width="1169" height="621" alt="2026-02-06 15 25 23" src="https://github.com/user-attachments/assets/af9e1eea-9aaf-4188-a84d-e0d111293b93" />

- original and inspiration article on Medium [here](https://medium.com/write-a-catalyst/i-made-an-ai-that-tells-me-what-i-actually-learned-online-each-day-001e1523693a)
- original GitHub repository [here](https://github.com/ManashWrites/I-Made-an-AI-That-Summarizes-My-Daily-Browsing-Into-a-2-Minute-Digest)

The original project by is an inspiration.

But it is not working out of the box on Windows (at least mine)
```repl
UnicodeEncodeError: 'charmap' codec can't encode character '\u200e' in position 1057: character maps to <undefined>
```

**An AI that summarizes your daily browsing into a 2-minute digest. 100% offline, 100% private.**

Ever wondered "What did I even read today?" This tool captures what you browse and uses a local AI to create a daily summary — no cloud, no tracking, no data leaving your machine.

## Features

- 🔒 **100% Private**: Everything runs locally. Your browsing data never leaves your machine.
- 🤖 **AI-Powered Summaries**: Uses Ollama with Llama 3.2 (or any local model) to generate insights.
- ⚡ **Lightweight**: Minimal extension that doesn't slow down your browser.
- 📊 **Smart Extraction**: Automatically extracts main content, skips ads and navigation.
- 📅 **Daily Digests**: Export any day's browsing and get a structured summary.

## How It Works

1. **Chrome Extension** captures page titles, URLs, and main content as you browse
2. **Export** your browsing data for any date (stored locally in browser)
3. **Python Script** sends the data to your local Ollama instance
4. **Get a Digest** with themes, insights, and action items

## Installation

### Prerequisites

1. install Ollama
2. pull your Model
3. **Start Ollama**:
   ```bash
   ollama serve
   ```

### Chrome Extension

1. Open Chrome and go to `chrome://extensions/`
2. Enable **Developer mode** (toggle in top right)
3. Click **Load unpacked**
4. Select the `extension` folder from this project
5. Pin the extension to your toolbar for easy access



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


## Usage

### 1. Browse the Web

Just browse normally. The extension automatically captures pages in the background.

### 2. Export Your Data

1. Click the Browsing Digest extension icon
2. Select a date (defaults to today)
3. Click **Export Today's Browsing**
4. Save the JSON file

### 3. Generate Your Digest
- run the llama.cpp server
- launch the summarizer with:
```bash
python dailyBrowsing_llamacpp.py browsing-digest-2026-02-06.json
```

This version gives you **full offline privacy** with the performance benefits of llama.cpp while maintaining all the robustness of your original tool. The API approach is also more stable than CLI piping (no more Unicode encoding issues on Windows!). 

