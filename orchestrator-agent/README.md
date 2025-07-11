# Orchestrator Agent - v0.4.0 Architecture

An A2A-compliant orchestration agent that coordinates tasks between multiple specialized agents using LangGraph.

## Architecture Overview

This implementation follows the v0.4.0 fully modular architecture pattern, featuring:

```
src/orchestrator_agent/
   core/               # LangGraph orchestration logic
   adapters/           # Protocol adapters
   protocol/           # A2A protocol implementation
   server/             # HTTP server with middleware
   client/             # Test client utilities
   common/             # Shared utilities
```

## Features

### Core Capabilities
- Multi-agent orchestration via A2A protocol
- Task decomposition and planning
- Parallel and sequential execution
- Result aggregation from multiple agents
- Error handling and fallback strategies
- LangGraph-based workflow orchestration

### v0.4.0 Architecture Features
- Modular subsystem design
- A2A protocol compliance
- Task lifecycle management
- Middleware stack (logging, CORS, error handling)
- Agent discovery via well-known endpoint
- Comprehensive error handling

## Prerequisites

- Python 3.12+
- uv package manager
- OpenAI or Google API key
- Two running A2A agents on localhost:10000 and localhost:10001

## Installation

```bash
# Clone and navigate to the directory
cd multiagent-adk/orchestrator-agent

# Install dependencies
uv sync

# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys and agent URLs
```

## Running the Orchestrator

```bash
# Start the orchestrator agent
uv run orchestrator-agent

# Or with custom settings
uv run orchestrator-agent --host 0.0.0.0 --port 10002
```

## Testing

```bash
# Run the test client
uv run python test_client.py

# Or test with curl
curl -X POST http://localhost:10002/message \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "messageId": "test-001",
        "role": "user",
        "parts": [{"text": "What is the USD to EUR rate and tell me about Python?"}],
        "contextId": "test"
      }
    },
    "id": 1
  }'
```

## API Endpoints

### A2A Standard Endpoints
- POST /message - Send message for orchestration
- GET /tasks/{id} - Get task status
- GET /tasks - List all tasks

### Discovery & Health
- GET /.well-known/agent.json - Agent capabilities
- GET /health - Health check

## Orchestration Flow

1. Planning Phase: Analyzes user request and creates orchestration plan
2. Routing Phase: Determines which agents handle which sub-tasks
3. Execution Phase: Sends tasks to remote agents and monitors progress
4. Aggregation Phase: Combines results into coherent response

## Configuration

### Environment Variables

```bash
# LLM Provider
OPENAI_API_KEY=your-key
# or GOOGLE_API_KEY=your-key

# Orchestrator Settings
A2A_HOST=localhost
A2A_PORT=10002

# Remote Agents
AGENT_1_URL=http://localhost:10000
AGENT_2_URL=http://localhost:10001

# Optional
LOG_LEVEL=INFO
REQUEST_TIMEOUT=30
MAX_CONCURRENT_TASKS=100
```

## Architecture Components

### Core Components
- OrchestratorState: LangGraph state management
- Agent: Main orchestration workflow
- Tools: Remote agent interaction tools

### Protocol Layer
- TaskManager: A2A task lifecycle
- MessageHandler: JSON-RPC processing
- AgentCard: Discovery metadata

### Adapters
- A2AExecutor: Bridges A2A with LangGraph
- LangGraphWrapper: Agent execution wrapper

## Example Orchestration

When you send: "What is the USD to EUR rate and tell me about Python?"

1. Planning: Identifies two sub-tasks
2. Routing: 
   - Currency question -> Agent 1 (Currency Agent)
   - Python question -> Agent 2 (General Agent)
3. Execution: Parallel execution of both tasks
4. Aggregation: Combines both responses

## Security

- Input validation at all layers
- Secure remote agent communication
- Error sanitization
- No hardcoded credentials

## Performance

- Async/await throughout
- Parallel task execution
- Connection pooling
- Efficient task management

## References

- [A2A Protocol](https://a2aproject.github.io/A2A/latest/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph)