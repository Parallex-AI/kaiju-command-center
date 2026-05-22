# Router

The Router receives incoming client requests and dispatches them to the appropriate agent.

## Responsibilities

- Parse and classify incoming requests
- Route to the correct agent (e.g., Ads Agent)
- Pass client context and memory along with the request
- Return the agent's response to the client

## Routing Rules (planned)

| Request Type         | Target Agent |
|----------------------|--------------|
| Ads performance      | ads-agent    |
| Campaign optimization| ads-agent    |

## Architecture Position

```
Client → Router → Agent → Response
```

## Status

MVP — structure only. No code yet.
