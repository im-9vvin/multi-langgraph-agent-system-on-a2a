# Time Agent - A2A Protocol v0.4.0 Architecture

Time and timezone conversion agent built with LangGraph and A2A Protocol, following the v0.4.0 architecture pattern.

## Quick Start

1. **Install dependencies**:
   ```bash
   uv sync
   ```

2. **Set up environment**:
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ```

3. **Run the server**:
   ```bash
   uv run time-agent
   ```
   
   The server will start on http://localhost:10001

4. **Test the agent**:
   ```bash
   # In another terminal
   uv run python examples/test_queries.py
   ```

## Features

- Get current time in any timezone
- Convert time between timezones
- Automatic system timezone detection
- Uses MCP Time Server for accurate timezone data
- Full A2A protocol compliance
- SSE streaming support
- State checkpointing and persistence

## Architecture

This agent follows the v0.4.0 architecture pattern with dedicated subsystems:

```
src/time_agent/
├── core/               # LangGraph agent logic
├── adapters/           # Protocol bridging
├── protocol/           # A2A protocol handling
├── streaming/          # SSE streaming subsystem
├── checkpointing/      # State persistence
├── server/             # FastAPI server
├── client/             # Test clients
└── common/             # Shared utilities
```

## Installation

```bash
uv sync
```

## Configuration

Create a `.env` file with:

```
OPENAI_API_KEY=your_openai_api_key
PORT=10001  # Default port for time-agent
LOCAL_TIMEZONE=UTC+9  # Your local timezone (optional)
MODEL_NAME=gpt-4o-mini  # OpenAI model to use (optional)
```

## Running

```bash
uv run time-agent
```

Or:

```bash
uv run python examples/run_server.py
```

## Usage

Send A2A protocol messages to get time information:

```json
{
  "jsonrpc": "2.0",
  "method": "message",
  "params": {
    "messages": [
      {
        "role": "user",
        "content": "What time is it in Tokyo?"
      }
    ]
  },
  "id": "1"
}
```

## API Endpoints

- `POST /message/send` - Send A2A messages
- `GET /message/stream` - SSE streaming endpoint
- `GET /tasks` - List tasks
- `GET /tasks/{id}` - Get task details
- `GET /.well-known/agent.json` - Agent discovery
- `GET /health` - Health check

## Development

```bash
# Run tests
uv run pytest

# Format code
uv run black src/

# Lint
uv run ruff check src/
```