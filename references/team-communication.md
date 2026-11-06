# Team Communication Protocol

## Purpose

This protocol makes agent collaboration real and auditable. It applies to the main dispatcher, the three default workers and every additional child agent.

## Authority Tree

The user is the root authority.

The main dispatcher reports directly to the user.

Each worker reports to exactly one direct supervisor.

A worker may become a supervisor only when the user or its direct supervisor authorizes a child.

The reporting tree is stored in `team_manifest.json`.

```json
{
  "trace_id": "codex-20261106-001",
  "team_name": "delivery-team",
  "root_supervisor": "dispatcher",
  "agents": [
    {
      "agent_id": "dispatcher",
      "name": "dispatcher",
      "role": "dispatch",
      "supervisor_id": "user",
      "thread_ref": "workbuddy-task:main",
      "status": "running"
    },
    {
      "agent_id": "research-agent",
      "name": "research-agent",
      "role": "research",
      "supervisor_id": "dispatcher",
      "thread_ref": "workbuddy-agent:research-agent",
      "status": "idle"
    }
  ]
}
```

The tree must contain no cycle. Every non-root agent must reference one existing supervisor.

## WorkBuddy Native Tools

Use these tools for a real team:

- `TeamCreate`: create the shared visible team.
- `Agent`: create an independent worker thread.
- `SendMessage`: send a task, question, answer, peer handoff or revision.
- `TaskOutput`: read a worker result.
- `TaskStop`: stop a worker when cancellation is authorized.
- `TeamDelete`: close a team after final consolidation when the tool is available.

The dispatcher must pass `name`, `subagent_type` and `team_name` to `Agent`.

The dispatcher must not pretend that a worker exists when `Agent` returns an error.

## Message Envelope

Every `SendMessage` payload should contain this information when the recipient needs structured work:

```json
{
  "trace_id": "codex-20261106-001",
  "message_id": "MSG-0001",
  "parent_message_id": null,
  "from": "dispatcher",
  "to": "research-agent",
  "supervisor_id": "dispatcher",
  "task_id": "T-1",
  "type": "task",
  "summary": "Research the three candidate options",
  "content": "Full task details and acceptance criteria",
  "artifacts": [],
  "requires_ack": true
}
```

Allowed message types:

| Type | Meaning |
|------|---------|
| `task` | New work assignment |
| `progress` | Status update |
| `question` | Request for clarification |
| `answer` | Response to a question |
| `handoff` | Transfer work to a child or peer |
| `revision` | Return defects for repair |
| `result` | Completed work |
| `blocker` | Work cannot continue |
| `cancel` | Stop the assigned branch |
| `complete` | Final upward report |

The sender must identify itself. The recipient must reply in its own thread. The recipient must route unresolved blockers to its direct supervisor.

## Visible Dialogue

Every worker must keep its ordinary WorkBuddy conversation visible. The dispatcher must not hide the work timeline.

At the end, the dispatcher reports:

- The team name.
- The reporting tree.
- Every agent name and thread reference.
- Every task assignment.
- Major questions, answers and peer handoffs.
- Every result, failure and revision.

The user may address any agent directly by name. The addressed agent must answer in its own thread and notify its direct supervisor.

## Background Waiting

After the dispatcher finishes all assignments, it returns control to the user and waits for worker messages or completion notifications.

The dispatcher must not busy-poll. When push notifications exist, wait for them. When polling is the only option, start with 30 to 60 seconds between checks and increase the interval after each unchanged result.

Report only a meaningful progress change, a blocker, a failure, or completion.

## Codex Bridge

When Codex creates the job, Codex supplies a `trace_id`, workspace, acceptance criteria and deliverables.

The Gateway sends the job to WorkBuddy as one top-level task. WorkBuddy creates the team and workers inside that task.

WorkBuddy returns:

- `track: CODEX_WORKBUDDY_RESULT:<job_id>`
- team name
- reporting tree
- agent thread references
- task results and evidence
- unresolved failures
- final acceptance recommendation

Codex verifies the deliverables independently. Codex does not treat a role-play transcript as proof of delegation.

## Failure Rules

If `TeamCreate` fails, stop before spawning workers.

If `Agent` fails for one worker, record the failure and continue only with workers that actually started.

If `SendMessage` fails, retry once. If it still fails, mark the branch blocked and report the failure to the user.

If a supervisor cannot reach its child, it must not fabricate the child's reply.

If the WorkBuddy native delegation tools remain unavailable, mark the task blocked with reason `NATIVE_AGENT_TOOLS_UNAVAILABLE`. Do not simulate the team.
