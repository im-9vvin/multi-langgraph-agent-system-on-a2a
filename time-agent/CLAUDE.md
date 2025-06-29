# Time Agent - Implementation Notes

## Overview

This is a Time and Timezone Agent built with LangGraph and A2A Protocol v0.4.0 architecture. It provides current time information and timezone conversion capabilities.

## Architecture

Follows the v0.4.0 fully modular architecture with dedicated subsystems:

### 1. Core Domain (`core/`)
- `agent.py`: LangGraph-based agent using ReAct pattern
- `tools.py`: Time operations (get current time, convert between timezones)
- `state.py`: Agent state management
- `prompts.py`: System prompts for the agent

### 2. Protocol Subsystem (`protocol/`)
- Full A2A protocol compliance
- Task lifecycle management
- Message validation and handling
- Agent discovery metadata

### 3. Streaming Subsystem (`streaming/`)
- Server-Sent Events (SSE) support
- Event queue with history for reconnection
- Stream conversion from LangGraph to SSE format

### 4. Checkpointing Subsystem (`checkpointing/`)
- State persistence with pluggable backends
- Memory backend implementation
- Task-checkpoint synchronization
- LangGraph checkpointer integration

### 5. Adapters (`adapters/`)
- `a2a_executor.py`: Main orchestrator for all subsystems
- `langgraph_wrapper.py`: Bridges LangGraph with A2A
- `state_translator.py`: Converts between message formats
- `stream_converter.py`: Adapts streaming between subsystems

### 6. Server (`server/`)
- FastAPI/Starlette application
- Middleware stack (CORS, logging, metrics, auth)
- Extended API endpoints beyond basic A2A
- SSE streaming endpoints

## Key Features

1. **Time Operations**:
   - Get current time in any IANA timezone
   - Convert times between timezones
   - Timezone alias support (EST, PST, etc.)
   - DST awareness

2. **A2A Compliance**:
   - Full protocol implementation
   - Task management
   - Agent discovery
   - JSON-RPC messaging

3. **Advanced Features**:
   - Real-time streaming via SSE
   - State persistence and recovery
   - Concurrent task handling
   - Comprehensive error handling

## Implementation Decisions

### 1. Simplified MCP Integration
Due to MCP package complexities, implemented direct timezone handling using `pytz` library. This provides:
- Full IANA timezone support
- DST calculations
- Reliable time conversions

In production, this would be replaced with actual MCP Time Server integration.

### 2. Model Choice
Uses OpenAI's `gpt-4o-mini` by default for cost-effectiveness while maintaining good performance.

### 3. Port Configuration
Default port is 8002 to avoid conflicts with currency-agent (8001).

## Running the Agent

1. Create `.env` file:
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

2. Install dependencies:
```bash
uv sync
```

3. Run the server:
```bash
uv run time-agent
```

Or:
```bash
uv run python examples/run_server.py
```

## Testing

Test with the included client:
```bash
uv run python src/time_agent/client/test_client.py
```

## API Endpoints

- `POST /message/send` - Send A2A messages
- `GET /message/stream` - SSE streaming
- `GET /tasks` - List tasks
- `GET /tasks/{id}` - Get task details
- `GET /.well-known/agent.json` - Agent discovery
- `GET /health` - Health check

## Example Queries

- "What time is it in Tokyo?"
- "What's the current time in New York?"
- "Convert 3:30 PM EST to London time"
- "What time is 14:00 in Paris when converted to Singapore?"
- "Show me the time difference between Los Angeles and Sydney"

## Future Enhancements

1. **MCP Integration**: Replace pytz implementation with actual MCP Time Server
2. **Historical Queries**: Add support for historical time queries
3. **Business Hours**: Add business hours calculations
4. **Time Zone Database**: Include timezone database updates
5. **Natural Language**: Enhanced NLU for time expressions

## Troubleshooting

1. **Import Errors**: Ensure all dependencies are installed with `uv sync`
2. **API Key**: Make sure OPENAI_API_KEY is set in .env
3. **Port Conflicts**: Change PORT in .env if 8002 is already in use
4. **Timezone Errors**: Use standard IANA timezone names or common aliases