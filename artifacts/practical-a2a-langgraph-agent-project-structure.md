# Practical A2A LangGraph Agent Project Structure

- version: v0.1.0

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
│       ├── server/             # A2A Server implementation
│       │   ├── __init__.py
│       │   ├── app.py          # FastAPI/Starlette app
│       │   ├── routes.py       # A2A protocol endpoints
│       │   ├── executor.py     # Task executor (LangGraph adapter)
│       │   ├── models.py       # Pydantic models for A2A
│       │   └── agent_card.py   # Agent card generator
│       │
│       ├── client/             # A2A Client implementation
│       │   ├── __init__.py
│       │   ├── client.py       # A2A client class
│       │   ├── discovery.py    # Agent discovery utilities
│       │   ├── auth.py         # Authentication handlers
│       │   └── models.py       # Client-side models
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
│   └── fixtures/
│       └── sample_tasks.json
│
├── examples/                   # Usage examples
│   ├── client_example.py       # How to use as client
│   ├── server_example.py       # How to run as server
│   └── combined_example.py     # Both roles example
│
├── docker/                     # Docker configurations
│   ├── Dockerfile
│   └── docker-compose.yml
│
└── docs/                       # Documentation
    ├── architecture.md
    ├── api.md
    └── deployment.md
```

# Focus on Streaminig

- Based on this structure, the files that would contain streaming control code are:

## 🎯 Primary Streaming Files:

1. src/agent_name/server/executor.py ⭐ (Most Important)

- Converts LangGraph async execution to A2A streaming events
- Implements TaskYieldUpdate generation
- Controls what gets streamed and when

2. src/agent_name/server/routes.py ⭐

- Handles /message/stream and /tasks/sendSubscribe endpoints
- Sets up Server-Sent Events (SSE) headers
- Formats A2A events for SSE transmission

3. src/agent_name/core/agent.py

- Implements LangGraph's astream() method
- Yields intermediate results during processing

## 🔄 Supporting Files:

4. src/agent_name/server/models.py

- Defines streaming event models (TaskYieldUpdate, etc.)

5. src/agent_name/client/client.py

- Consumes streams when acting as a client
- Handles SSE parsing and event processing

6. src/agent_name/common/utils.py

- Helper functions for SSE formatting
- Streaming utility functions

The executor.py and routes.py are the most critical files where you'll implement the majority of your streaming logic!
