# Multi LangGraph Agent System on A2A Protocol Context

# Project Goals and Characteristics

- This project aims to make Github template repositories and CLI tools for quick and easy scaffolding a "Multi LangGraph Agents System on A2A Protocol" project base. These are the superficial outputs.
- On the other hand, the true and most important goals of this project are "complete understanding about the tech stacks" of me and "growing application capabilities with the tech stacks" of me. Even it may not have visible outputs.
- Write researching reports for individual series of concepts.
- Develop interactive .html mindmap for unified knowledge graphs. Use "MemoryMesh MCP tools" or "Mindmap MCP tools".

# Major Programming Lanaguage

- You basically code in Python(>=3.12) under this project context except only if I explicitly order you to use the other programming languages.

# Major Python Project(package) Manager

- You use "uv" as a python prjoect(package) manager.
- It's official documentations are here: "https://docs.astral.sh/uv/".

# "A2A" and "LangGraph"

- "A2A" means "Agent to Agent protocol".
- It's official specifications, implementations and sample projects are shown on "https://github.com/a2aproject".
- It's official documentations are here: "https://a2aproject.github.io/A2A/latest/".
- When you plan to code about A2A you sholud refer them firstly.

- "LangGraph" means "An Agent Development Framework, LangGraph".
- It's official documentations are here: "https://langchain-ai.github.io/langgraph".
- When you plan to code about LangChain you should refer that firstly.

# Cautions about OS and CLI Terminal Shell

- This project's code base is on WSL2(Ubuntu 24.04.2 LTS) file system which is hosted on Windows 11.
- So, before using cli commands MUST VERIFY which shell you are currently in and use appropriate cli commands for each shell.
- WSL Ubuntu bash shell is recommended.

# Project Directory Structures.

- On the WSL Ubuntu filesystem, the project root directory is represented as: `/home/march/workbench/im-9vvin/multi-langgraph-agent-system-on-a2a`.
- The same directory is represented on the Powershell or Windows cmd as: `\\wsl$\Ubuntu\home\march\workbench\im-9vvin\multi-langgraph-agent-system-on-a2a\`
- This project directory is managed by git and it has a remote github repository: "https://github.com/im-9vvin/multi-langgraph-agent-system-on-a2a.git". Once you made valuable documents it will commit/push to remote and re-serve as the Project Knowledges(a Claude Desktop's feature).
- As follwing the project's characteristcs, It is not to aim to fine structured, production level program code base. It is closer to playground directory. Don't let structures to bother creativities.
- Make a new directory for every each tests, researchs, PoCs, following tutorials.

## Work History

### Currency Agent Architecture Evolution (2025-06-29)

Successfully created `currency-agent-v0.4.0` by converting the v0.2.0 architecture implementation to the most sophisticated v0.4.0 fully modular architecture:

1. **Duplicated** `currency-agent-concised` (v0.2.0) → `currency-agent-v0.4.0`
2. **Added Protocol Subsystem**: Task management, message handling, validation
3. **Added Streaming Subsystem**: SSE support, stream conversion, event queuing
4. **Added Checkpointing Subsystem**: State persistence, synchronization, recovery
5. **Enhanced Adapters**: Full orchestration with all subsystems
6. **Enhanced Server**: Middleware stack, extended endpoints, authentication

Key achievements:
- Preserved all A2A compliance and LangGraph patterns
- Added enterprise features while maintaining backward compatibility
- Successfully tested with `uv sync` - all dependencies resolved
- Comprehensive documentation in README.md and CLAUDE.md

The v0.4.0 implementation demonstrates the most advanced architecture pattern for A2A + LangGraph agents.
