# Currency Exchange Agent - v0.4.0 Architecture

This is a Currency Exchange Agent built with the **v0.4.0 fully modular architecture** of the A2A + LangGraph agent pattern. It demonstrates the most sophisticated integration of the A2A (Agent-to-Agent) protocol with LangGraph's agent framework.

## 🏗️ Architecture Overview

### v0.4.0 - Fully Modular Architecture

This implementation follows the v0.4.0 architecture specification, featuring:

```
src/currency_agent/
├── core/               # LangGraph agent logic
├── adapters/           # Protocol adapters
├── protocol/           # A2A protocol implementation
├── streaming/          # SSE streaming subsystem
├── checkpointing/      # State persistence
├── server/             # HTTP server with middleware
├── client/             # A2A client implementation
└── common/             # Shared utilities
```

### Key Subsystems

1. **Protocol Subsystem** (`protocol/`)
   - Dedicated A2A protocol handling
   - Task lifecycle management
   - Message validation and routing
   - Agent card generation

2. **Streaming Subsystem** (`streaming/`)
   - Server-Sent Events (SSE) implementation
   - Stream conversion from LangGraph
   - Event queuing and delivery
   - Reconnection support

3. **Checkpointing Subsystem** (`checkpointing/`)
   - Custom A2A checkpointer
   - State synchronization
   - Multiple storage backends
   - Task recovery capabilities

4. **Enhanced Adapters** (`adapters/`)
   - LangGraph wrapper with checkpointing
   - State translation between formats
   - Full orchestration in executor

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- `uv` package manager
- API keys for LLM providers

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd currency-agent-v0.4.0

# Install dependencies with uv
uv sync

# Copy environment template
cp .env.example .env
# Edit .env with your API keys
```

### Running the Agent

```bash
# Start the A2A server
uv run currency-agent

# Or with custom host/port
uv run currency-agent --host 0.0.0.0 --port 8080
```

### Testing the Agent

```bash
# Quick test to verify responses are working (RECOMMENDED)
uv run python test_fixed.py

# Run the full test client
uv run python src/currency_agent/client/test_client.py

# Or use curl for direct API testing
curl -X POST http://localhost:10000/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "messageId": "test-001",
        "role": "user",
        "parts": [{"text": "What is USD to EUR rate?"}],
        "contextId": "test"
      }
    },
    "id": 1
  }'
```

## 📋 Features

### Core Capabilities
- ✅ Real-time currency conversion using Frankfurter API
- ✅ Exchange rate lookups with historical data
- ✅ Multi-currency calculations
- ✅ Natural language understanding

### v0.4.0 Advanced Features
- ✅ **Streaming Responses**: Real-time SSE streaming
- ✅ **Checkpointing**: State persistence and recovery
- ✅ **Task Management**: Full lifecycle tracking
- ✅ **Authentication**: A2A auth bridge
- ✅ **Middleware Stack**: Logging, CORS, error handling
- ✅ **Agent Discovery**: Well-known agent card endpoint
- ✅ **Reconnection Support**: Event history for dropped connections

## 🔧 Configuration

### Environment Variables

```bash
# LLM Provider (choose one)
OPENAI_API_KEY=your-openai-key
GOOGLE_API_KEY=your-google-key

# Optional configurations
A2A_HOST=localhost
A2A_PORT=10000
LOG_LEVEL=INFO
CHECKPOINT_INTERVAL=30
MAX_CONCURRENT_TASKS=100
```

### Agent Card Configuration

The agent card is automatically generated at `/.well-known/agent.json`:

```json
{
  "name": "currency-agent-v040",
  "version": "0.4.0",
  "capabilities": [
    "currency_conversion",
    "exchange_rate_lookup",
    "streaming_responses",
    "task_checkpointing"
  ],
  "endpoints": {
    "message": "/message",
    "stream": "/message/stream",
    "tasks": "/tasks",
    "health": "/health"
  }
}
```

## 🔌 API Endpoints

### Standard A2A Endpoints
- `POST /message` - Send message to agent
- `POST /tasks/create` - Create new task
- `GET /tasks/{id}` - Get task status

### v0.4.0 Extended Endpoints
- `POST /message/stream` - Stream responses via SSE
- `GET /tasks/{id}/stream` - Stream task events
- `POST /tasks/sendSubscribe` - Subscribe to multiple tasks
- `GET /tasks` - List all tasks with filtering
- `POST /tasks/{id}/cancel` - Cancel running task
- `GET /.well-known/agent.json` - Agent discovery
- `GET /health` - Health check with metrics

## 🏛️ Architecture Details

### Protocol Subsystem
- **TaskManager**: Manages task lifecycle and state transitions
- **MessageHandler**: Processes JSON-RPC messages
- **ProtocolValidator**: Validates messages and data
- **AgentCardGenerator**: Creates discovery metadata

### Streaming Subsystem
- **SSEHandler**: Manages SSE connections and lifecycle
- **StreamConverter**: Converts LangGraph streams to SSE
- **EventQueue**: Buffers events with history support
- **SSEFormatter**: Formats events for transmission

### Checkpointing Subsystem
- **A2ACheckpointer**: LangGraph-compatible checkpointer
- **StateSynchronizer**: Syncs A2A tasks with checkpoints
- **StorageBackend**: Abstract storage interface
- **MemoryBackend**: In-memory implementation (Redis backend available)

### Middleware Stack
1. **ErrorHandlingMiddleware**: Global exception handling
2. **CORSMiddleware**: Cross-origin resource sharing
3. **LoggingMiddleware**: Request/response logging
4. **AuthenticationMiddleware**: A2A authentication

## 🧪 Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src

# Run specific test categories
uv run pytest tests/unit/
uv run pytest tests/integration/
```

## 🐛 Debugging

### Enable Debug Logging
```bash
export LOG_LEVEL=DEBUG
uv run currency-agent
```

### Monitor Streaming Events
```bash
# Watch SSE stream
curl -N http://localhost:10000/tasks/{task_id}/stream
```

### Check Task Status
```bash
# List all tasks
curl http://localhost:10000/tasks

# Get specific task
curl http://localhost:10000/tasks/{task_id}
```

## 🔒 Security

- Environment-based configuration
- A2A authentication support
- Input validation at all layers
- Error messages sanitized
- No hardcoded secrets

## 📈 Performance

- Async/await throughout
- Event streaming for real-time updates
- Connection pooling for HTTP clients
- Efficient checkpointing
- Configurable queue sizes

## 🤝 Contributing

This is a reference implementation showcasing v0.4.0 architecture patterns. When contributing:

1. Maintain the modular structure
2. Add tests for new features
3. Update documentation
4. Follow Python best practices
5. Use type hints consistently

## 📚 References

- [A2A Protocol Specification](https://a2aproject.github.io/A2A/latest/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph)
- [v0.4.0 Architecture Spec](../artifacts/practical-a2a-langgraph-agent-project-structure-v0.4.0.md)

## ⚖️ License

This project follows the same license as the original A2A samples repository.