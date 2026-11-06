# External AI Integration

## Scope

The team can mix WorkBuddy-native agents and external AI agents.

External AI agents are declared in a local JSON registry. Each external agent receives the same message envelope used by native agents.

The external agent log is stored under the run's `dialogue` directory. The user can inspect the full request, response, timestamp, transport and exit status.

## Supported Transports

| Transport | Use |
|-----------|-----|
| `cli` | Call a locally installed AI CLI without a shell |
| `http` | Call a JSON HTTP or HTTPS endpoint |
| Native WorkBuddy `Agent` | Create a visible WorkBuddy worker thread |
| WorkBuddy connector plus `ToolSearch` and `DelegateTool` | Use an installed MCP connector inside a worker |
| A2A | Use the WorkBuddy A2A tools when the endpoint supports A2A |

Do not pass secrets in chat text. Reference environment variables with values such as `"${EXTERNAL_AI_API_KEY}"`.

## Registry

Create a registry outside the Skill directory, preferably in the user project.

```json
{
  "agents": {
    "codex-cli": {
      "transport": "cli",
      "kind": "coding_agent",
      "command": [
        "C:\\path\\to\\codex.exe",
        "exec",
        "--skip-git-repo-check",
        "--sandbox",
        "workspace-write",
        "--json",
        "-C",
        "${WORKSPACE}",
        "-"
      ],
      "cwd": "${WORKSPACE}",
      "timeout_seconds": 600
    },
    "generic-http-ai": {
      "transport": "http",
      "kind": "external_agent",
      "url": "${EXTERNAL_AI_URL}",
      "method": "POST",
      "headers": {
        "authorization": "Bearer ${EXTERNAL_AI_API_KEY}"
      },
      "timeout_seconds": 600
    }
  }
}
```

## Message Contract

Every external agent receives one JSON object:

```json
{
  "trace_id": "codex-20261106-001",
  "message_id": "MSG-0001",
  "from": "dispatcher",
  "to": "codex-cli",
  "supervisor_id": "dispatcher",
  "task_id": "T-1",
  "type": "task",
  "summary": "Review the proposed architecture",
  "content": "Full task and evidence requirements",
  "artifacts": [],
  "acceptance_criteria": [
    "Return concrete findings",
    "Return evidence paths"
  ]
}
```

The external agent must return a JSON object or a readable final report. Codex must not treat an HTTP status alone as task completion.

## Invocation

Use the bundled adapter:

```powershell
python scripts\external_agent_adapter.py `
  --config C:\path\to\external_agents.json `
  --agent codex-cli `
  --message '{"trace_id":"trace-1","from":"dispatcher","to":"codex-cli","type":"task","content":"Review the plan"}' `
  --dialogue C:\path\to\run\dialogue\codex-cli.jsonl
```

The adapter does not use a shell. CLI arguments must be an array. HTTP headers and URLs may reference environment variables.

## Hierarchy

An external AI may be a direct child of the dispatcher or a child of any authorized worker.

The external AI has one `supervisor_id`. Its parent records all requests and responses in the parent thread.

External AI cannot create an invisible chain. If an external AI supports child agents, its parent must receive the child IDs and message transcript references.

## Failure Handling

| Error | Action |
|-------|--------|
| Missing environment variable | Stop the branch and report the variable name |
| HTTP authentication failure | Stop the branch and do not retry without new authorization |
| HTTP timeout | Retry once when the request is read-only |
| CLI timeout | Mark the branch failed and retain stderr |
| Invalid response | Mark the result unverified |

No secret value may be written to the dialogue file.
