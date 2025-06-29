# Currency Agent - Project Context and History

## Origin

This project started as a sample from the A2A project repository:

- Original source: `https://github.com/a2aproject/a2a-samples/tree/main/samples/python/agents/langgraph`
- Initial structure: Simple flat structure with all logic in `app/` directory

## Transformation Journey

### 1. Initial State

- Basic A2A + LangGraph integration sample
- All code in a single `app/` directory
- Minimal separation of concerns
- Working but not following best practices

### 2. Architecture Analysis

We analyzed multiple architecture versions from our best practices:

- [v0.1.0](../artifacts/practical-a2a-langgraph-agent-project-structure-v0.1.0.md): Basic modular structure with core/server/client separation
- [v0.2.0](../artifacts/practical-a2a-langgraph-agent-project-structure-v0.2.0.md): Added adapters layer for protocol bridging
- [v0.3.0](../artifacts/practical-a2a-langgraph-agent-project-structure-v0.3.0.md): Added persistence/checkpointing capabilities
- [v0.4.0](../artifacts/practical-a2a-langgraph-agent-project-structure-v0.4.0.md): Fully modular with dedicated subsystems ✅ **CURRENT**

### 3. Evolution from v0.2.0 to v0.4.0

#### Previous Implementation (v0.2.0)
The `currency-agent-concised` folder used v0.2.0 architecture:
- Simple adapters layer
- Basic protocol bridging
- Minimal subsystems

#### Current Implementation (v0.4.0)
This folder implements the **most sophisticated v0.4.0 architecture**:

```
src/currency_agent/
├── core/               # LangGraph agent logic (preserved)
├── adapters/           # Enhanced protocol adapters
├── protocol/           # NEW: Dedicated protocol subsystem
├── streaming/          # NEW: SSE streaming subsystem
├── checkpointing/      # NEW: State persistence subsystem
├── server/             # Enhanced with middleware stack
├── client/             # A2A client utilities
└── common/             # Shared utilities
```

## v0.4.0 Architecture Implementation

### 1. **Protocol Subsystem** (`protocol/`)
- `agent_card_generator.py`: Creates A2A discovery metadata
- `task_manager.py`: Full task lifecycle management
- `message_handler.py`: JSON-RPC message processing
- `models.py`: Type-safe protocol models
- `validators.py`: Protocol validation logic

### 2. **Streaming Subsystem** (`streaming/`)
- `sse_handler.py`: Server-Sent Events management
- `stream_converter.py`: LangGraph → SSE conversion
- `event_queue.py`: Event buffering with history
- `formatters.py`: SSE formatting utilities

### 3. **Checkpointing Subsystem** (`checkpointing/`)
- `a2a_checkpointer.py`: Custom LangGraph checkpointer
- `state_synchronizer.py`: Task ↔ checkpoint sync
- `storage_backend.py`: Abstract storage interface
- `memory_backend.py`: In-memory implementation

### 4. **Enhanced Adapters** (`adapters/`)
- `a2a_executor.py`: Full orchestration with all subsystems
- `langgraph_wrapper.py`: LangGraph with checkpointing
- `state_translator.py`: Format translation utilities

### 5. **Enhanced Server** (`server/`)
- `app.py`: v0.4.0 feature configuration
- `routes.py`: Extended API endpoints
- `middleware.py`: Full middleware stack
- `authentication.py`: A2A auth bridge

## Key v0.4.0 Features Added

1. **Advanced Streaming**
   - Real-time SSE support
   - Reconnection handling
   - Event history for dropped connections
   - Stream format conversion

2. **State Persistence**
   - Task checkpointing
   - State recovery
   - Multiple backend support
   - Auto-sync capabilities

3. **Protocol Management**
   - Full task lifecycle
   - Message validation
   - Agent discovery
   - JSON-RPC handling

4. **Middleware Stack**
   - Error handling
   - CORS support
   - Request logging
   - Authentication

5. **Extended API**
   - `/message/stream` - SSE streaming
   - `/tasks/{id}/stream` - Task event stream
   - `/tasks` - Task listing with filters
   - `/.well-known/agent.json` - Discovery
   - `/health` - Health metrics

## Technical Stack

- **Python**: >=3.12
- **Package Manager**: uv (Astral)
- **LLM Framework**: LangGraph (LangChain)
- **Protocol**: A2A (Agent-to-Agent)
- **API**: Frankfurter API for exchange rates
- **Server**: Uvicorn with Starlette
- **Architecture**: v0.4.0 (Fully Modular)

## Important Notes

1. Always use `uv` commands, not direct Python
2. This implements the **most advanced v0.4.0 structure**
3. All LangGraph patterns preserved and enhanced
4. A2A compliance maintained with extended features
5. Production-ready with all enterprise features

## Migration Path

From v0.2.0 → v0.4.0:
1. Core logic preserved (no breaking changes)
2. Added dedicated subsystems
3. Enhanced adapters with full orchestration
4. Extended API with streaming/checkpointing
5. Backward compatible with v0.2.0 clients

## Implementation Journey & Fixes

### Initial Implementation Issues
1. **Over-engineered streaming**: Initially tried to use complex event bridging between subsystems
2. **Wrong A2A SDK methods**: Attempted to use `yield_value()` which doesn't exist on TaskUpdater
3. **Async complexity**: Multiple layers of async streaming prevented proper response delivery

### Resolution
Fixed by simplifying the executor while keeping v0.4.0 architecture:
- Used direct streaming from agent (like v0.2.0)
- Correct A2A SDK methods: `add_artifact()`, `complete()`, `update_status()`
- Removed unnecessary event bridging complexity
- Maintained all v0.4.0 subsystems but simplified the flow

### Testing Considerations
The A2A protocol is asynchronous by design:
- `message/send` returns immediately with task status
- Actual responses come later through task completion
- Test scripts must poll or use A2A client SDK for proper response handling
- See `test_fixed.py` for proper polling implementation

### Final State
✅ All v0.4.0 subsystems implemented and functional
✅ Responses properly delivered to clients
✅ Checkpointing and state management working
✅ Protocol validation and task management operational
✅ Clean, maintainable code structure
