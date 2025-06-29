# A2A Protocol Quick Reference: Methods, Parts, and Events

## Communication Patterns (RPC Methods)

### Message Methods
| Method | Purpose | Response Type |
|--------|---------|---------------|
| `message/send` | Send a message synchronously | `Task` or `Message` |
| `message/stream` | Send a message with SSE streaming | SSE stream of events |

### Task Management Methods
| Method | Purpose | Response Type |
|--------|---------|---------------|
| `tasks/get` | Retrieve current task state | `Task` |
| `tasks/cancel` | Request task cancellation | `Task` |
| `tasks/resubscribe` | Reconnect to SSE stream | SSE stream of events |

### Push Notification Methods
| Method | Purpose | Response Type |
|--------|---------|---------------|
| `tasks/pushNotificationConfig/set` | Configure webhook URL | `TaskPushNotificationConfig` |
| `tasks/pushNotificationConfig/get` | Retrieve push config | `TaskPushNotificationConfig` |
| `tasks/pushNotificationConfig/list` | List all push configs | `TaskPushNotificationConfig[]` |
| `tasks/pushNotificationConfig/delete` | Remove push config | `null` |

### Agent Discovery
| Method | Purpose | Response Type |
|--------|---------|---------------|
| `agent/authenticatedExtendedCard` | Get authenticated agent card (HTTP GET) | `AgentCard` |

## Part Types (Content Units)

### TextPart
```json
{
  "kind": "text",
  "text": "Your text content here",
  "metadata": { /* optional */ }
}
```

### FilePart
```json
{
  "kind": "file",
  "file": {
    "name": "example.pdf",
    "mimeType": "application/pdf",
    "bytes": "base64data..."  // OR "uri": "https://..."
  },
  "metadata": { /* optional */ }
}
```

### DataPart
```json
{
  "kind": "data",
  "data": {
    "any": "structured",
    "json": "content"
  },
  "metadata": { /* optional */ }
}
```

## Streaming Event Types

### Task Event
```json
{
  "id": "task-id",
  "contextId": "context-id",
  "status": { "state": "working" },
  "kind": "task",
  "artifacts": [],
  "history": []
}
```

### Message Event
```json
{
  "role": "agent",
  "parts": [/* Part objects */],
  "kind": "message",
  "messageId": "msg-id",
  "taskId": "task-id",
  "contextId": "context-id"
}
```

### Status Update Event
```json
{
  "taskId": "task-id",
  "contextId": "context-id",
  "kind": "status-update",
  "status": {
    "state": "working",
    "message": { /* optional Message */ },
    "timestamp": "2024-03-15T10:00:00Z"
  },
  "final": false
}
```

### Artifact Update Event
```json
{
  "taskId": "task-id",
  "contextId": "context-id",
  "kind": "artifact-update",
  "artifact": {
    "artifactId": "artifact-id",
    "name": "Result",
    "parts": [/* Part objects */]
  },
  "append": false,
  "lastChunk": false
}
```

## Task States

| State | Description | Terminal? |
|-------|-------------|-----------|
| `submitted` | Task received but not started | No |
| `working` | Task actively being processed | No |
| `input-required` | Waiting for user input | No (Paused) |
| `auth-required` | Waiting for authentication | No (Paused) |
| `completed` | Task finished successfully | **Yes** |
| `failed` | Task terminated with error | **Yes** |
| `canceled` | Task was canceled | **Yes** |
| `rejected` | Task rejected by agent | **Yes** |
| `unknown` | Task state cannot be determined | **Yes** |

## Extension Points

### Where Extensions Are Allowed
- **Agent Card**: `capabilities.extensions[]`
- **Messages**: `metadata` and `extensions[]` fields
- **Tasks**: `metadata` field
- **Artifacts**: `metadata` and `extensions[]` fields
- **Parts**: `metadata` field on all part types

### What Cannot Be Extended
- ❌ Custom RPC methods (only built-in methods allowed)
- ❌ Custom Part types (only text, file, data)
- ❌ Custom Task states (only the 9 defined states)
- ❌ Protocol transport (must use HTTP/HTTPS)
- ❌ Message format (must use JSON-RPC 2.0)

## Key Capabilities Flags

| Capability | Default | Description |
|------------|---------|-------------|
| `streaming` | `false` | Supports SSE streaming (`message/stream`, `tasks/resubscribe`) |
| `pushNotifications` | `false` | Supports webhook notifications |
| `stateTransitionHistory` | `false` | Exposes detailed task state history |
| `supportsAuthenticatedExtendedCard` | `false` | Provides extended agent card when authenticated |

## Notes

- All methods except `agent/authenticatedExtendedCard` use JSON-RPC 2.0 over HTTP POST
- SSE streaming uses `Content-Type: text/event-stream`
- Each SSE event contains a JSON-RPC response in its `data` field
- The `kind` field serves as a type discriminator in multiple contexts (Parts, Events, Objects)
- The `metadata` field allows custom data without breaking protocol compliance