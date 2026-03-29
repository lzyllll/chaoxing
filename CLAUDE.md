# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Chaoxing (超星学习通) automation tool for completing course tasks. Dual-mode architecture:
- **CLI Mode**: Command-line interface via `main.py`
- **Web Mode**: FastAPI backend + Vue3 frontend for multi-account management

**Critical**: This is an educational automation tool. Follow GPL-3.0 license requirements.

## Architecture

### Dual Entry Points

```
CLI Mode:
  main.py → chaoxing.services.runner.run_study() → chaoxing.core.base.Chaoxing

Web Mode:
  web_api.py → chaoxing.web.app (FastAPI) → chaoxing.services.runner (async tasks)
  frontend/ (Vue3 + Vite) → API calls to backend
```

### Package Structure

```
chaoxing/
├── core/          # Base API, config, exceptions, logging
│   └── base.py    # Chaoxing class - main API wrapper
├── services/      # External integrations
│   ├── answer.py  # Question bank (Tiku) providers
│   ├── notification.py
│   └── runner.py  # Task execution orchestration
├── processors/    # Task handlers (video, live, etc.)
├── utils/         # Utilities (decode, cipher, fonts)
└── web/           # Web interface (FastAPI + SQLModel)
    ├── api/       # REST endpoints
    ├── ws/        # WebSocket for real-time updates
    ├── models/    # SQLModel entities
    ├── services/  # Business logic
    └── settings.py # Backend config from config.yaml
```

### Key Design Patterns

1. **Singleton HTTP Session**: `SessionManager` in `core/base.py` ensures single session across all requests
2. **Factory Pattern**: `Tiku.get_tiku_from_config()` creates question bank providers dynamically
3. **Strategy Pattern**: Different task types (video, document, quiz) use different processors
4. **Producer-Consumer**: `JobProcessor` uses `PriorityQueue` for concurrent chapter processing

### Configuration System

- **CLI Mode**: `config.ini` (from `config_template.ini`)
- **Web Mode**: `config.yaml` (from `config.example.yaml`) + `frontend/.env`
- Web accounts can override default question bank settings per-account

## Development Commands

### Setup

```bash
# Install dependencies
pip install -r requirements.txt
# or
pip install .
```

### Run CLI Mode

```bash
# Interactive
python main.py

# With config file
python main.py -c config.ini

# With arguments
python main.py -u <phone> -p <password> -l <course_ids> -s 1.5 -j 4 -v
```

### Run Web Mode

```bash
# Backend (from project root)
python web_api.py
# or with uv
uv run --python 3.13 web_api.py

# Frontend (in frontend/ directory)
cd frontend
npm install
npm run dev

# Or use PowerShell script (starts both)
.\run-web.ps1
```

### Build Executable

```bash
pip install pyinstaller
pyinstaller -F main.py -n 'chaoxing' --add-data "resource;resource" --hidden-import=chardet
```

## Web Architecture Details

### Backend (FastAPI + SQLModel + SQLite)

- **Entry**: `web_api.py` → `chaoxing.web.app.create_app()`
- **Database**: SQLite via SQLModel, auto-created on startup
- **API Routes**:
  - `/api/accounts` - Account CRUD
  - `/api/tasks` - Task management and execution
  - `/api/decisions` - User decision handling
  - `/ws` - WebSocket for real-time task updates
- **Settings**: `chaoxing.web.settings.get_backend_settings()` reads `config.yaml`
- **Task Execution**: Async via `chaoxing.services.runner` with WebSocket progress updates

### Frontend (Vue3 + Vite)

- **Location**: `frontend/` directory
- **Stack**: Vue3, TypeScript, Vite, Element Plus
- **Config**: `frontend/.env` for API/WS endpoints
- **Build**: `npm run build` → `frontend/dist/`

### Data Flow (Web Mode)

```
User → Vue3 UI → REST API → FastAPI → runner.run_study() → Chaoxing API
                                    ↓
                                WebSocket → Real-time updates → Vue3 UI
```

## Common Modification Scenarios

### Add New Question Bank Provider

1. Create class in `chaoxing/services/answer.py` inheriting from `Tiku`
2. Implement `init_tiku()` and `query()` methods
3. Add config section to `config_template.ini` and `config.example.yaml`

### Add New Task Type

1. Add handler in `chaoxing/processors/` if complex logic needed
2. Update `chaoxing/core/base.py` Chaoxing class with new method
3. Update `chaoxing/services/runner.py` to call new handler

### Modify Concurrency

- CLI: Adjust `-j` parameter or `jobs` in config.ini
- Web: Modify `chaoxing/services/runner.py` ThreadPoolExecutor settings
- Chapter-level: `JobProcessor` in runner.py
- Task-level: `ThreadPoolExecutor` in individual processors

## Debugging

```bash
# Enable debug logging
python main.py -v

# Web backend debug
# Set server.reload=true in config.yaml

# Check logs
# CLI: stdout or chaoxing.log (if configured)
# Web: uvicorn logs + SQLite database at .runtime/chaoxing.db
```

## Important Notes

- **Python 3.13+** required (uses modern type hints like `dict[str, Any]`)
- **Thread Safety**: Be careful with shared state; SessionManager handles HTTP session
- **Font Decoding**: Chaoxing uses custom fonts; see `utils/font_decoder.py` and `resource/font_map_table.json`
- **Question Banks**: Require API tokens; see config templates for provider-specific settings
- **Closed Tasks**: `notopen_action` config controls behavior (retry/ask/continue)

## Code Conventions

- UTF-8 encoding with `# -*- coding: utf-8 -*-` header
- Type annotations using Python 3.10+ syntax
- Loguru for logging (not stdlib logging)
- Custom exceptions in `chaoxing/core/exceptions.py`
- PEP 8 style

## Testing

No automated test suite currently. Manual testing approach:
- Test with real accounts (use test accounts)
- Verify different task types (video, document, quiz, live)
- Test question bank integrations
- Verify concurrent chapter processing
