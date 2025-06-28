# Understanding A2A Protocol Architecture: Components, Relationships, and Implementation Patterns

## A2A operates on a simplified client-server model with no "Host" component

The Agent-to-Agent (A2A) protocol, developed by Google, fundamentally differs from other protocols like MCP by implementing a **streamlined two-component architecture**: A2A Client and A2A Server (also called Remote Agent). The protocol **does not define an "A2A Host" component**, which represents a key architectural decision emphasizing open implementation and distributed agent communication.

The A2A Client initiates requests and consumes services from A2A Servers on behalf of users or systems. It discovers available agents through Agent Cards (JSON metadata published at `/.well-known/agent.json`), creates and manages tasks, handles authentication, and processes responses including streaming updates via Server-Sent Events (SSE). Clients communicate using JSON-RPC 2.0 over HTTPS with modern TLS encryption.

The A2A Server or Remote Agent exposes HTTP endpoints that implement the A2A protocol methods. It publishes an Agent Card describing its capabilities and authentication requirements, processes incoming tasks through defined lifecycle states (submitted, working, input-required, completed, failed, canceled), generates artifacts as outputs, and supports both synchronous and streaming communication patterns. Servers maintain task state throughout interactions and can send push notifications for long-running operations.

## Component relationships follow a flexible, distributed architecture

The A2A protocol enables direct client-to-server communication with remarkable flexibility in deployment patterns. Clients discover servers through Agent Cards, authenticate using declared schemes (OAuth2, API keys, JWT), and send structured task requests. The communication flow follows a clear pattern: discovery → authentication → task initiation → processing → result delivery.

**Key interaction patterns include:**
- **Direct Communication**: Clients communicate directly with servers using HTTP/JSON-RPC
- **Peer-to-Peer Capability**: Any A2A server can act as a client to other servers, enabling hierarchical task delegation
- **No Client-to-Client Communication**: Clients don't communicate directly; all interaction goes through servers
- **Fully Distributed**: Components can be geographically distributed across different cloud providers and organizations

The protocol supports both synchronous request-response patterns (`tasks/send`) and streaming interactions (`tasks/sendSubscribe`). For streaming, servers maintain SSE connections to provide real-time status updates, partial results, and progress notifications. This architecture allows agents to collaborate across organizational boundaries without requiring shared memory, tools, or co-location.

## LangGraph implementation demonstrates complete A2A server architecture

The LangGraph-based agent implementation at the specified repository provides a **complete A2A server implementation** showcasing production-ready patterns. This currency conversion agent demonstrates how sophisticated LangGraph agents integrate with the A2A protocol through an elegant adapter pattern.

The implementation consists of four key components. The **Agent Implementation** uses LangGraph's ReAct pattern with Google Gemini LLM and maintains conversation state through checkpoints. The **Agent Executor** serves as the critical adapter layer, translating between LangGraph's execution model and A2A's task-oriented approach, handling both synchronous and streaming responses. The **Server Setup** provides full A2A protocol compliance through a Starlette-based HTTP server with proper Agent Card discovery. Finally, **Helper Functions** manage the transformation between LangGraph's internal representations and A2A protocol events.

The implementation maps LangGraph concepts to A2A elegantly: LangGraph's state transitions become A2A task states, tool invocations generate streaming status updates, and final results transform into A2A artifacts. It supports multi-turn conversations through context preservation, demonstrates input-required states when clarification is needed, and provides real-time updates during processing. The entire stack uses async/await patterns for non-blocking execution and includes robust error handling with appropriate A2A error responses.

## Agents relate through task delegation and service consumption

In the A2A ecosystem, agents establish relationships primarily through the **task delegation pattern**. An agent implementation typically embodies one or both roles: as a client that delegates tasks to specialized agents, or as a server that provides specific capabilities to other agents. This creates natural agent networks where specialized agents (like a currency converter or weather service) are consumed by orchestrator agents that coordinate complex workflows.

The protocol enables several collaboration patterns. **Sequential processing** allows a client to delegate to Server A, which can then delegate subtasks to Server B. **Parallel processing** enables clients to simultaneously delegate to multiple servers for efficiency. **Hierarchical delegation** supports any depth of agent-to-agent delegation, with each server potentially acting as a client to others. These patterns work seamlessly across different agent frameworks, vendors, and deployment environments.

Agent discovery happens through Agent Cards that act as "digital business cards," describing capabilities, endpoints, and authentication requirements. This discovery mechanism, combined with standard web protocols, enables dynamic agent ecosystems where new specialized agents can be added without modifying existing infrastructure.

## Implementation flexibility allows separate or combined components

**A2A-compliant agents have complete freedom in how they implement protocol components.** There is no requirement to implement all roles in a single agent. The protocol supports three primary implementation patterns:

**Separate Components** represent the most flexible approach, where client agents, server agents, and any user-facing applications are completely independent. This pattern excels in microservices architectures and enables specialized teams to develop and maintain different components. For example, a company might develop client agents for orchestration while consuming third-party server agents for specialized tasks.

**Combined Implementations** merge client and server capabilities in a single agent, useful for agents that both provide services and coordinate with others. This pattern simplifies deployment for smaller systems while maintaining full protocol compliance. The agent can receive tasks as a server while delegating subtasks as a client.

**Specialized Roles** allow agents to implement only what they need. A weather service might only implement the server role, while a user-facing orchestrator might primarily act as a client. This flexibility enables efficient resource usage and clear architectural boundaries.

## Terminology reflects architectural simplicity and flexibility

The A2A protocol uses precise terminology that reflects its architectural design:

- **A2A-compliant agent**: Any agent implementing the A2A protocol specification, regardless of which components it includes
- **A2A Client / Client agent**: An agent or application that initiates tasks and consumes A2A services
- **A2A Server / Remote agent**: An agent exposing HTTP endpoints that receive and process tasks according to A2A protocol
- **Agent Card**: The JSON metadata document describing an agent's capabilities, hosted at the well-known URI

Agents are typically named functionally based on their primary capability (Weather Agent, Translation Agent, Analysis Agent) rather than their architectural role. This naming convention emphasizes what agents do rather than how they're implemented, supporting the protocol's goal of abstracting implementation details from consumers.

The term "A2A-compliant" indicates conformance to the protocol specification without implying any particular implementation pattern. This terminology deliberately avoids prescriptive labels, allowing maximum flexibility in how organizations structure their agent ecosystems while maintaining interoperability through protocol compliance.

## Conclusion

The A2A protocol's elegant simplicity—with just Client and Server components rather than a Host-Client-Server trinity—enables remarkable flexibility in building interoperable agent ecosystems. By eliminating the Host component and focusing on direct agent-to-agent communication, the protocol reduces architectural complexity while maintaining enterprise-grade security and scalability. The LangGraph implementation exemplifies how sophisticated agent frameworks can seamlessly integrate with A2A, demonstrating that the protocol's simplicity doesn't limit functionality but rather enables it through clear, focused design.