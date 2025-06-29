# Practical A2A LangGraph Agent Project Structure (with Checkpointing)

- version: v0.3.0

```
a2a-agent-example/
├── pyproject.toml              # uv project configuration
├── uv.lock                     # uv lock file
├── .env.example                # Environment variables template
├── .gitignore
├── README.md
│
├── src/
│   └── agent_name/             # Replace with your agent name
│       ├── __init__.py
│       │
│       ├── core/               # Core agent logic
│       │   ├── __init__.py
│       │   ├── agent.py        # LangGraph agent implementation
│       │   ├── state.py        # Agent state definitions
│       │   ├── tools.py        # Agent tools/functions
│       │   └── prompts.py      # System prompts
│       │
│       ├── adapters/           # Protocol adapters
│       │   ├── __init__.py
│       │   ├── a2a_executor.py      # Bridge between A2A and LangGraph
│       │   ├── langgraph_wrapper.py  # Wraps LangGraph agents for A2A
│       │   ├── state_translator.py   # Converts between state formats
│       │   ├── message_converter.py  # A2A Message <-> LangGraph format
│       │   ├── stream_converter.py   # Streaming format conversion
│       │   └── checkpointing.py      # State synchronization (NEW)
│       │
│       ├── server/             # A2A Server implementation
│       │   ├── __init__.py
│       │   ├── app.py          # FastAPI/Starlette app
│       │   ├── routes.py       # A2A protocol endpoints
│       │   ├── models.py       # Pydantic models for A2A
│       │   ├── agent_card.py   # Agent card generator
│       │   ├── task_manager.py # Task lifecycle management
│       │   └── task_store.py   # Task persistence (NEW)
│       │
│       ├── client/             # A2A Client implementation
│       │   ├── __init__.py
│       │   ├── client.py       # A2A client class
│       │   ├── discovery.py    # Agent discovery utilities
│       │   ├── auth.py         # Authentication handlers
│       │   └── models.py       # Client-side models
│       │
│       ├── persistence/        # Persistence layer (NEW)
│       │   ├── __init__.py
│       │   ├── checkpointer.py # Custom checkpointer implementation
│       │   ├── memory_store.py # In-memory storage
│       │   └── redis_store.py  # Redis-based storage
│       │
│       ├── common/             # Shared utilities
│       │   ├── __init__.py
│       │   ├── config.py       # Configuration management
│       │   ├── logging.py      # Logging setup
│       │   ├── exceptions.py   # Custom exceptions
│       │   └── utils.py        # Helper functions
│       │
│       └── main.py             # Entry point for the agent
│
├── static/                     # Static files for agent card
│   └── .well-known/
│       └── agent.json          # Generated agent card
│
├── tests/
│   ├── __init__.py
│   ├── test_agent.py
│   ├── test_server.py
│   ├── test_client.py
│   ├── test_adapters.py       # Adapter-specific tests
│   ├── test_persistence.py     # Persistence tests (NEW)
│   └── fixtures/
│       └── sample_tasks.json
│
├── examples/                   # Usage examples
│   ├── client_example.py       # How to use as client
│   ├── server_example.py       # How to run as server
│   ├── combined_example.py     # Both roles example
│   └── checkpoint_example.py   # Checkpointing example (NEW)
│
├── docker/                     # Docker configurations
│   ├── Dockerfile
│   └── docker-compose.yml
│
└── docs/                       # Documentation
    ├── architecture.md
    ├── api.md
    ├── deployment.md
    ├── adapters.md             # Adapter documentation
    └── checkpointing.md        # Checkpointing guide (NEW)
```

# Focus on Streaming

- Based on this structure, the files that would contain streaming control code are:

## 🎯 Primary Streaming Files:

1. **src/agent_name/adapters/a2a_executor.py** ⭐ (Most Important)
   - Main orchestration of streaming logic
   - Coordinates between A2A protocol and LangGraph execution
   - Implements TaskYieldUpdate generation
   - Integrates with checkpointing for state consistency

2. **src/agent_name/adapters/stream_converter.py** ⭐
   - Dedicated streaming format conversion
   - Converts LangGraph async streams to A2A SSE events
   - Handles token batching and event formatting
   - Maintains streaming state in checkpoints

3. **src/agent_name/server/routes.py** ⭐
   - Handles `/message/stream` and `/tasks/sendSubscribe` endpoints
   - Sets up Server-Sent Events (SSE) headers
   - Routes streaming requests to adapters
   - Manages streaming session lifecycle

4. **src/agent_name/core/agent.py**
   - Implements LangGraph's `astream()` method
   - Yields intermediate results during processing

## 🔄 Supporting Files:

5. **src/agent_name/adapters/checkpointing.py** (NEW)
   - Ensures streaming state persists across reconnections
   - Synchronizes A2A task state with LangGraph checkpoints
   - Handles stream recovery after disconnection

6. **src/agent_name/adapters/state_translator.py**
   - Translates streaming state between formats
   - Maintains state consistency during streaming

7. **src/agent_name/server/models.py**
   - Defines streaming event models (TaskYieldUpdate, etc.)

8. **src/agent_name/client/client.py**
   - Consumes streams when acting as a client
   - Handles SSE parsing and event processing

9. **src/agent_name/common/utils.py**
   - Helper functions for SSE formatting
   - Streaming utility functions

The addition of checkpointing ensures reliable streaming even with connection interruptions!