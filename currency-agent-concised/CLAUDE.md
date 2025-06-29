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
- [v0.2.0](../artifacts/practical-a2a-langgraph-agent-project-structure-v0.1.0.md): Added adapters layer for protocol bridging ✅ **Selected**
- [v0.3.0](../artifacts/practical-a2a-langgraph-agent-project-structure-v0.1.0.md): Added persistence/checkpointing capabilities
- [v0.4.0](../artifacts/practical-a2a-langgraph-agent-project-structure-v0.1.0.md): Fully modular with dedicated subsystems

### 3. Restructuring Decision

Selected **v0.2.0** for the following reasons:

- **Optimal Balance**: Not overly complex but provides good separation
- **Adapter Pattern**: Clean bridge between A2A protocol and LangGraph
- **Uniformity**: Consistent structure for future agents
- **Extensibility**: Easy to add features without major refactoring
- **Maintainability**: Clear boundaries between components

### 4. Implementation

Restructured the entire codebase following v0.2.0:

```
src/currency_agent/
├── core/           # LangGraph agent logic
├── adapters/       # A2A ↔ LangGraph bridge
├── server/         # A2A server implementation
├── client/         # A2A client utilities
└── common/         # Shared utilities
```

## Key Improvements Made

1. **Separation of Concerns**

   - A2A protocol logic separated from LangGraph implementation
   - Clean adapter pattern for protocol translation
   - Modular structure for each responsibility

2. **Code Organization**

   - Tools extracted to dedicated module
   - Prompts and state definitions separated
   - Configuration centralized
   - Custom exceptions hierarchy

3. **Enhanced Documentation**

   - Comprehensive comments in all Python files
   - Detailed README with architecture explanation
   - Clear indication of v0.2.0 structure adoption

4. **Developer Experience**
   - Consistent use of `uv` package manager
   - CLI entry points for easy execution
   - Test client for verification
   - Environment-based configuration

## Technical Stack

- **Python**: >=3.12
- **Package Manager**: uv (Astral)
- **LLM Framework**: LangGraph (LangChain)
- **Protocol**: A2A (Agent-to-Agent)
- **API**: Frankfurter API for exchange rates
- **Server**: Uvicorn with Starlette

## Important Notes

1. Always use `uv` commands, not direct Python
2. This follows our best practices v0.2.0 structure
3. Designed as a reference implementation for future agents
4. Comments are mandatory in all Python files

## Future Considerations

- Can be upgraded to v0.3.0 if checkpointing needed
- Structure supports multiple agents in same codebase
- Ready for production deployment with minor additions
