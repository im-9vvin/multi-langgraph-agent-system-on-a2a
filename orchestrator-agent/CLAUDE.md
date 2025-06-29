# Orchestrator Agent - Project Context

## Purpose

This is an A2A-compliant orchestration agent that demonstrates how to coordinate multiple specialized agents using the A2A protocol and LangGraph framework.

## Architecture

Follows the v0.4.0 fully modular architecture pattern with dedicated subsystems:

- **Core**: LangGraph-based orchestration workflow
- **Adapters**: Bridges A2A protocol with LangGraph
- **Protocol**: Full A2A protocol implementation
- **Server**: HTTP server with middleware stack

## Key Design Decisions

### 1. Orchestration Flow

The agent uses a 4-phase orchestration flow:
1. **Planning**: Analyzes requests and creates execution plans
2. **Routing**: Determines which agents handle which sub-tasks
3. **Execution**: Sends tasks to remote agents and monitors progress
4. **Aggregation**: Combines results into coherent responses

### 2. A2A Compliance

- Implements standard A2A endpoints (/message, /tasks)
- Follows JSON-RPC protocol
- Provides agent discovery via .well-known/agent.json
- Manages task lifecycle properly

### 3. Remote Agent Integration

- Designed to work with any A2A-compliant agents
- Currently configured for:
  - Agent 1 (localhost:10000): Currency exchange specialist
  - Agent 2 (localhost:10001): General purpose agent
- Uses agent cards for capability discovery

### 4. Error Handling

- Graceful degradation when agents fail
- Partial result delivery
- Comprehensive error reporting

## Testing

The test_client.py demonstrates various orchestration scenarios:
- Single agent routing
- Multi-agent parallel execution
- Result aggregation
- Error handling

## Future Enhancements

1. **Streaming Support**: Add SSE streaming for real-time updates
2. **Checkpointing**: Add state persistence for long-running orchestrations
3. **Dynamic Discovery**: Auto-discover available agents
4. **Advanced Routing**: ML-based routing decisions
5. **Load Balancing**: Distribute tasks across multiple instances of same agent type

## Integration Points

This orchestrator can coordinate:
- Currency agents (exchange rates, conversions)
- General knowledge agents
- Code generation agents
- Data analysis agents
- Any A2A-compliant agent

## Important Notes

1. Always ensure remote agents are running before starting orchestrator
2. Configure environment variables properly (.env file)
3. The orchestrator itself runs on port 10002 by default
4. Uses OpenAI or Google AI for planning and aggregation