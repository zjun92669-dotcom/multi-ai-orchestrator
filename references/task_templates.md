# Task Templates and Decomposition Rules

## Task Ticket Format

Every sub-task in the orchestration system is represented as a task ticket in JSON format:

```json
{
  "id": "T-1",
  "role": "research",
  "description": "Analyze the existing codebase structure and identify refactoring opportunities",
  "expected_output": "Structured report listing current architecture, pain points, and recommended changes",
  "dependencies": [],
  "supervisor_id": "dispatcher",
  "assigned_agent": "research-agent-1",
  "agent_kind": "workbuddy",
  "external_ai_id": null,
  "dispatch_strategy": "fixed",
  "write_paths": [],
  "acceptance_criteria": "Report covers at least 3 refactoring opportunities with specific file references"
}
```

### Field Specifications

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | Yes | Unique identifier, format: `T-{number}` (e.g., T-1, T-2) |
| role | string | Yes | One of: "research", "execution", "qa" |
| description | string | Yes | Clear description of what the sub-task involves |
| expected_output | string | Yes | Description of the expected result format and content |
| dependencies | list[string] | Yes | List of task IDs this task depends on. Empty list if none. |
| supervisor_id | string | Yes | The direct supervisor's agent ID. Use `user` only for the root supervisor. |
| assigned_agent | string | Yes | The unique WorkBuddy agent name created by `Agent`. |
| agent_kind | string | No | `workbuddy`, `external_cli`, or `external_http`. Defaults to `workbuddy`. |
| external_ai_id | string or null | Conditional | Required when `agent_kind` starts with `external_`. Must match a registry entry. |
| dispatch_strategy | string | No | `fixed`, `random`, `round_robin`, or `priority`. Defaults to `fixed`. |
| write_paths | list[string] | Conditional | Required for execution role. List of file paths the agent may write to. Must be empty or omitted for research and qa roles. |
| acceptance_criteria | string | Optional | Specific criteria for QA verification. Required if role is "qa" or if a qa task depends on this task. |

## Decomposition Rules

### Rule 1: Role Identification

When analyzing a user request, classify each component:

- **Research component**: The request requires information gathering, analysis, or evaluation before any action can be taken. Examples: "analyze the current state", "find all files matching X", "evaluate options for Y".
- **Execution component**: The request requires creating, modifying, or producing files or content. Examples: "create a report", "write a script", "generate a config file".
- **QA component**: The request requires verification that produced output meets specific criteria. Examples: "ensure the code follows best practices", "verify the report is complete".

### Rule 2: Dependency Ordering

Tasks must be ordered by dependency:

1. Research tasks run first (no dependencies, or depend only on other research tasks).
2. Execution tasks run after their prerequisite research tasks complete.
3. QA tasks run after their corresponding execution tasks complete.

```text
Research (T-1) ─┐
                ├─→ Execution (T-3) ──→ QA (T-5)
Research (T-2) ─┘
```

The task dependency graph is separate from the reporting tree. A task dependency may cross agent branches. A reporting relationship must always point to one declared supervisor.

### Rule 3: Random Assignment Criteria

A set of sub-tasks qualifies for random assignment only when ALL of the following conditions are met:

1. **Simple**: Each task can be completed in a single agent invocation without complex multi-step reasoning.
2. **Homogeneous**: All tasks in the set have the same type and require the same capability.
3. **Independent**: No task in the set depends on the output of another task in the set.
4. **Qualified agents exist**: At least one agent has the required capability in its `capabilities` list.

If any condition is not met, the task must be assigned to a specific agent by the dispatcher.

### Rule 4: Task Granularity

Each task ticket should represent a unit of work that:
- Can be completed by a single agent in one invocation
- Has a clear, verifiable output
- Does not mix research and execution in the same task

If a task is too large for a single agent invocation, split it into multiple smaller tasks with appropriate dependencies.

## Example Decomposition Scenarios

### Scenario 1: "Create a data analysis report from CSV files"

```
T-1 (research): Read and analyze the structure of all CSV files in /data/
    dependencies: []
    supervisor_id: dispatcher
    assigned_agent: research-agent-1
    
T-2 (research): Identify key metrics and trends in the data
    dependencies: [T-1]
    supervisor_id: dispatcher
    assigned_agent: research-agent-1

T-3 (execution): Generate analysis report markdown file
    dependencies: [T-2]
    supervisor_id: dispatcher
    assigned_agent: execution-agent-1
    write_paths: ["/output/analysis_report.md"]

T-4 (qa): Verify the report covers all identified metrics
    dependencies: [T-3]
    supervisor_id: dispatcher
    assigned_agent: qa-agent-1
    acceptance_criteria: "Report contains sections for each metric identified in T-2"
```

### Scenario 2: "Format 5 independent log files into structured JSON"

```
T-1 (execution, randomly assignable): Format /logs/app.log into JSON
    dependencies: []
    write_paths: ["/output/app.json"]

T-2 (execution, randomly assignable): Format /logs/error.log into JSON
    dependencies: []
    write_paths: ["/output/error.json"]

T-3 (execution, randomly assignable): Format /logs/access.log into JSON
    dependencies: []
    write_paths: ["/output/access.json"]

T-4 (execution, randomly assignable): Format /logs/debug.log into JSON
    dependencies: []
    write_paths: ["/output/debug.json"]

T-5 (execution, randomly assignable): Format /logs/system.log into JSON
    dependencies: []
    write_paths: ["/output/system.json"]

T-6 (qa): Verify all 5 JSON files are valid and follow the required schema
    dependencies: [T-1, T-2, T-3, T-4, T-5]
    acceptance_criteria: "All output files are valid JSON with fields: timestamp, level, message"
```

For T-1 through T-5: since they are simple, homogeneous, and independent, they qualify for random assignment using `scripts/random_assign.py`.

### Scenario 3: "Research API options, implement the chosen one, and verify it works"

```
T-1 (research): Evaluate 3 API options for weather data
    dependencies: []

T-2 (execution): Implement the chosen API integration
    dependencies: [T-1]
    write_paths: ["/src/weather_api.py", "/config/api_config.json"]

T-3 (qa): Verify the implementation handles errors and returns valid data
    dependencies: [T-2]
    acceptance_criteria: "Code handles 404, 500, and timeout errors. Returns temperature and humidity fields."
```
