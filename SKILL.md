---
name: multi-ai-orchestrator
description: "WorkBuddy 多 AI 团队调度器。用户说启动多 AI 调度、让三个 AI 分工讨论、安排调研执行验收、指定谁当主管、给代理增加下级、查看每个代理对话、接入 Codex 或其他外部 AI、或通过 Codex 后台同步协作时使用。A dispatcher creates a visible WorkBuddy team, supports user-selected supervisors, recursive delegation, native Agent and SendMessage communication, transcript audit, external AI adapters, and two-way Codex handoff. Do not use for ordinary questions or single-step tasks."
---

# Multi-AI Orchestrator

## Overview

This skill transforms a WorkBuddy task into a visible multi-agent team. The main dispatcher decomposes complex work into research, execution, and verification tasks. The default team has three members. Each member may receive an additional child agent when the user assigns one and the task justifies it.

The user is always the root authority. The main dispatcher is the user's direct subordinate. Every additional agent reports to exactly one direct supervisor. A supervisor may supervise more agents. The full chain must remain visible and auditable.

Use native WorkBuddy `Agent` and `SendMessage` tools. Never describe one model alternating roles as a multi-agent team. If native delegation fails, report the failure and stop the affected branch.

Codex is the first external AI integration. Other AI services may join through the bundled CLI or HTTP adapter, WorkBuddy connectors, MCP tools, or A2A tools. External agents use the same task and message envelope as native agents.

## Non-Negotiable Rules

1. Create the team with `TeamCreate` before starting worker tasks when the tool is available.
2. Launch every real worker with `Agent`.
3. Give every worker a unique `name`, a `subagent_type`, and the same `team_name`.
4. Put the worker role, task ticket, direct supervisor, reporting rule and conversation contract in the Agent prompt.
5. Every delegation, progress update, question, answer, revision and result must use `SendMessage`.
6. The user must be able to open every agent thread and inspect its complete dialogue and tool timeline.
7. A child reports to its direct supervisor. The supervisor forwards the consolidated status upward.
8. A worker may create its own children only when the user or its supervisor explicitly authorizes that branch.
9. A worker must not contact an unrelated peer without copying its supervisor.
10. A single-session role-play does not satisfy this Skill's multi-agent requirement.

## Trigger Conditions

Activate this skill when the user says any of the following:
- "launch multi-AI dispatch" / "start multi-AI scheduling"
- "split work among three AIs" / "divide labor among three agents"
- "assign research/execution/QA AI"
- "randomly assign simple tasks to qualified members"
- "use the orchestrator for this task"
- "specify who is the supervisor"
- "add a child agent to this worker"
- "show me every agent conversation"
- "let the agents talk to each other"
- "give this agent two subordinates"

When triggered, the dispatcher must enter Phase 1 (task decomposition) first. The dispatcher must not modify any files until the user confirms the work breakdown.

### Invocation Modes

1. Manual invocation: the user selects this Skill by name or slash command.
2. Automatic invocation: an enabled Skill description matches an explicit request for three-member division, parallel research/execution/QA work, or random assignment among qualified workers.

### Do Not Trigger

Do not activate this Skill when:

- The request is a normal question or a single-step task.
- The user did not request multi-agent work or three-member division.
- The goal or expected deliverable is too unclear to define acceptance criteria.
- The task is a one-off creative exploration without a stable process.
- The task has high-impact permissions or side effects and no explicit approval boundary.
- The user only asks about the Skill itself.

## Authority and Reporting Tree

The team is a tree, not an unlabeled group chat.

```text
User
└── Dispatcher
    ├── Research Agent
    ├── Execution Agent
    └── QA Agent
        └── Optional QA Child Agent
```

The user may choose any supervisor. If the user does not choose one, the main dispatcher is the direct supervisor of the three default members.

Every agent record must include:

- `agent_id`: stable unique identifier
- `name`: the name used by `Agent` and `SendMessage`
- `role`: research, execution, qa, or a user-defined specialist role
- `supervisor_id`: exactly one direct supervisor
- `team_name`: the shared WorkBuddy team name
- `status`: idle, running, waiting, completed, failed, cancelled
- `thread_ref`: the WorkBuddy agent thread or task identifier
- `current_task_id`: active task ticket

The supervisor owns assignment, dependency management, message routing, rework decisions and upward reporting. A worker owns only its assigned branch and direct children.

Direct user instructions outrank the current chain. If the user addresses a specific agent, route the instruction to that agent and copy its direct supervisor. Never create a hidden side conversation.

Use `SendMessage` for all inter-agent communication. Use `TaskOutput` to retrieve work. Use `SendMessage` again to relay feedback or revision requests.

Every agent message is visible in its WorkBuddy thread. The dispatcher must preserve the thread references in the final report. Do not replace the native threads with a private simulation.

In the WorkBuddy desktop UI, the user can inspect the team member cards and the `Agents` tabs. Every worker must open its own visible thread before accepting work. The dispatcher must remind the user that all threads remain available for inspection.

## Scope and Suitability

Use this Skill for repeated processes with stable steps, clear boundaries, and explicit acceptance criteria. Good examples include repeated codebase audits, structured research from independent sources, and independent file transformations.

Do not use this Skill for vague ideation, ordinary chat, one-off tasks, highly unstable workflows, or high-risk operations without approval and verification rules.

If the request looks relevant but lacks a clear deliverable, scope, write boundary, or acceptance standard, ask one concise clarification before dispatching workers.

## Architecture

### Roles and Permissions

The default team has three fixed base roles. Each role has a specific tool restriction enforced at the instruction level. See `references/agent_profiles.md` for full role definitions.

| Role | Tool Access | Input | Output |
|------|------------|-------|--------|
| Research Agent | Read, Grep, Glob, WebSearch, WebFetch only | Task ticket + context | Structured research report |
| Execution Agent | Write, Edit to specified paths only; Read for context | Task ticket + write paths + context | Produced files + execution log |
| QA Agent | Read, Grep, Glob only | Execution output + acceptance criteria | QA report (pass/fail + defect list) |

All three base members may carry the `general_simple` capability. This capability is only for simple, homogeneous, independent, low-risk tasks. It does not replace the professional boundaries above.

Additional agents may be added only by a supervisor with explicit user permission or an explicit delegation rule. Each child inherits a narrower scope, one direct supervisor and the existing team name.

### Required Agent Launch Shape

Use the WorkBuddy native tools in this order:

1. `TeamCreate` with a clear `team_name`, description and lead.
2. `Agent` for each worker with `name`, `subagent_type`, `team_name` and a complete task prompt.
3. `SendMessage` for the initial task handoff when the worker needs an explicit message.
4. `TaskOutput` for completion retrieval.
5. `SendMessage` for questions, peer coordination and upward progress.

The dispatcher must record the returned agent name and task identifier. The dispatcher must not claim that a worker exists until `Agent` succeeds.

### Permission Boundary (Current Phase: Soft Constraint)

The current implementation enforces tool restrictions through Agent prompt instructions. This is a soft constraint: the dispatcher instructs each sub-agent to use only its permitted tools. A future phase will upgrade to hard constraints via WorkBuddy's Expert system configuration.

The dispatcher must log all tool calls made by sub-agents. If a sub-agent violates its tool restrictions, the dispatcher flags the violation in the final report.

## Workflow: 6 Phases

### Phase 1: Task Reception and Decomposition

The dispatcher receives the user's request and performs the following:

1. Analyze the request to identify components requiring research, execution, and verification.
2. Split the request into sub-tasks. Each sub-task has:
   - A unique ID (format: `T-{number}`)
   - A role assignment (research / execution / qa)
   - A description of the work
   - Expected output format
   - Dependencies on other sub-tasks (if any)
   - A direct supervisor
   - A target agent name
   - A trace ID shared with Codex when applicable
3. For multiple simple, homogeneous, independent, low-risk sub-tasks: mark them as assignable and select `random`, `round_robin`, `least_load`, `capability_score`, or `external_first`. Record the chosen strategy and seed.
4. Present the work breakdown to the user in a structured table.

The dispatcher must not start any sub-agent in this phase.

### Phase 2: User Confirmation

The dispatcher presents the work breakdown and explicitly asks the user to confirm. The presentation must include:

- Sub-task list with IDs, roles, descriptions
- The full reporting tree, including every direct supervisor
- Assignment method (fixed or random with seed)
- Estimated execution order (parallel or sequential)
- How the user can open each agent thread and inspect its full dialogue
- Any identified risks or constraints

The dispatcher waits for user confirmation. If the user modifies the plan, return to Phase 1 and adjust.

### Phase 3: Member Selection and Assignment

After user confirmation, the dispatcher finalizes assignments:

1. For fixed-assignment sub-tasks: assign directly to the corresponding role.
2. Professional or dependent sub-tasks stay assigned to the Research, Execution, or QA role.
3. For assignable tasks, first filter qualified members by required capability and availability. Simple generic tasks may use `general_simple`. Run `scripts/dispatch_engine.py` with the following:
   ```bash
   python scripts/dispatch_engine.py --tasks <task_list_json> --agents <agent_list_json> --strategy <strategy> --seed <seed_value>
   ```
   If no seed is provided, the script generates one from the current timestamp and records it.
4. Validate all task tickets using `scripts/task_validator.py`:
   ```bash
   python scripts/task_validator.py --tickets <tickets_json>
   ```
5. Record the final assignment plan including the strategy, seed value and reporting tree.
6. Call `TeamCreate` when available. Use one stable `team_name` for the whole run.

### Phase 4: Parallel Execution

The dispatcher launches sub-agents using the Agent tool. For each sub-task:

1. Construct the sub-agent prompt based on its role profile (see `references/agent_profiles.md`).
2. Include in the prompt:
   - The full task ticket
   - The team name, assigned name, direct supervisor and reporting rule
   - All relevant context (the user's original request, any prior sub-task outputs)
   - The tool restriction for the role
   - The expected output format
   - The requirement to keep its full dialogue in its own visible thread
3. Launch the Agent with `run_in_background: true` for parallel execution.
4. The dispatcher monitors completion via TaskOutput.
5. The dispatcher uses `SendMessage` to send progress requests, questions, peer handoffs and revision instructions.

**Research and Execution agents run in parallel** if they have no dependencies. QA agents always run after their corresponding Execution agents complete.

After all tasks are dispatched, the dispatcher waits for agent messages or completion notifications. The dispatcher must not busy-poll or keep generating status text while the team works. If the runtime has no push notification, use sparse status checks with a 30 to 60 second interval and increase the interval after each unchanged check.

For launching agents, use the Agent tool with:
- `name: "<unique-agent-name>"`
- `subagent_type: "general-purpose"`
- `team_name: "<shared-team-name>"`
- `run_in_background: true`

Use a role-specific name such as `research-agent-1`, `execution-agent-1` or `qa-agent-1`.

To send follow-up messages to a running agent, use `SendMessage` with the agent name as the recipient. Every task, answer, peer handoff and revision must use `SendMessage`. The dispatcher must not invent a worker reply.

If a worker needs a child, it must use its own `Agent` and `SendMessage` calls, record the child's `supervisor_id` as its own `agent_id`, and use the same team name. The child reports upward through its supervisor.

### Phase 5: Verification

After Execution agents complete, the dispatcher launches QA agents:

1. Collect the execution output (file paths, logs, produced artifacts).
2. Construct the QA agent prompt with:
   - The execution output
   - The acceptance criteria from the original task ticket
   - The tool restriction (read-only)
3. Launch the QA agent.
4. Wait for the QA report.

If the QA report is "fail":
1. Extract the defect list.
2. Send the defects back to the Execution agent via SendMessage.
3. Wait for the Execution agent to fix and resubmit.
4. Re-run QA. Maximum 2 rounds of fix-verify cycles.

If QA still fails after 2 rounds, mark the sub-task as "failed" and continue.

### Phase 6: Consolidation and Report

The dispatcher collects all results and generates a final report using `assets/report_template.md`:

1. Summarize completed sub-tasks (with outputs).
2. List failed sub-tasks (with failure reasons).
3. Record fix-verify cycles (rounds, defects, resolutions).
4. Record the random seed used (if any).
5. Record any tool restriction violations.
6. Include the team name and hierarchical reporting tree.
7. Include every agent thread reference and a concise transcript index.
8. Present the report to the user.

## Failure Handling

See `references/failure_handling.md` for the complete failure handling protocol.

Summary of failure handling levels:

| Level | Trigger | Action |
|-------|---------|--------|
| L1 | Sub-agent timeout or crash | Retry once. Second failure: mark sub-task as failed, continue others. |
| L2 | QA rejection | Send defects to Execution agent. Max 2 fix-verify rounds. |
| L3 | Overall task cannot complete | Consolidate completed and failed parts. Output structured report. |

## Resource Reference

### Installation

- Preferred WorkBuddy UI: open "专家·技能·连接器", choose "添加技能", then "上传技能", select the ZIP, enable "非高风险自动安装", and confirm the security scan.
- Observed user install path: `~/.workbuddy-ai/skills/multi-ai-orchestrator/`.
- Compatibility copy path: `~/.codebuddy/skills/multi-ai-orchestrator/`.
- Package root: the ZIP must contain `SKILL.md` with YAML `name` and `description`. This package also contains `.codebuddy-plugin/plugin.json`.

After installation, verify that the Skill appears under "已安装技能" and shows "去试试". A local upload does not create a marketplace listing or `skill_*` marketplace ID.

### scripts/

- `dispatch_engine.py`: Multi-strategy task assignment engine. Supports round-robin, least-load, capability-score, external-first strategies. Accepts task list JSON, agent list JSON, strategy name, and optional seed. Outputs assignment result, seed value, and strategy used.
- `random_assign.py`: Legacy reproducible random task assignment. Retained for backward compatibility. Prefer `dispatch_engine.py` for new tasks.
- `task_validator.py`: Validates task ticket format. Checks required fields, role validity, dependency consistency, dispatch strategy validity, and external executor fields.
- `team_manifest_validator.py`: Validates the reporting tree, unique agent names and supervisor references.
- `external_agent_adapter.py`: Calls a declared external AI through a shell-free CLI adapter or JSON HTTP adapter and records the exchange.

### references/

- `agent_profiles.md`: Full role definitions, tool restrictions, prompt templates for each of the three agent roles, and external AI member profiles.
- `task_templates.md`: Task ticket format specification, decomposition rules, dispatch strategy definitions, and external executor fields.
- `failure_handling.md`: Detailed failure handling protocol with decision trees, including L4 for external AI failures.
- `team-communication.md`: Agent tree, direct messaging, visible dialogue and Codex trace protocol.
- `external-ai-integration.md`: External AI registry, CLI and HTTP adapters, secrets and A2A guidance. Covers Codex Gateway, MCP Server, and HTTP API connection types.
- `workbuddy-video-guidelines.md`: Skill design, triggering, iteration, and distribution lessons extracted from the referenced video.
- `distribution-and-license.md`: Local installation, public source, open-source claims, and license requirements.
- `codex-background-sync.md`: Codex-to-WorkBuddy background dispatch (passive mode) and WorkBuddy-to-Codex reverse dispatch (active mode).

### assets/

- `report_template.md`: Markdown template for the final consolidated report.
- `team_manifest.example.json`: Example hierarchy manifest.
- `external_agents.example.json`: Example registry for Codex CLI and a generic HTTP AI.

## Key Constraints

1. The dispatcher must present the work breakdown and obtain user confirmation before any file modification.
2. Research and QA agents are read-only. Execution agents write only to user-specified paths.
3. Multi-strategy assignment is only for simple, homogeneous, independent sub-tasks. The seed and strategy must be recorded.
4. Maximum 2 fix-verify rounds per failed sub-task.
5. The dispatcher must preserve every agent thread and record all delegation and message events for audit purposes.
6. The default team has three members: one Research, one Execution and one QA. The user may assign another supervisor or add child agents when needed.
7. Simple `general_simple` tasks may use multi-strategy assignment among qualified and idle members. Professional tasks remain fixed by role.
8. Current read/write isolation is a soft constraint. Hard isolation requires a later WorkBuddy expert-system test.
9. Codex synchronization uses the external Codex WorkBuddy Gateway. Do not install that Gateway control Skill inside WorkBuddy.
10. Every real worker must be created with `Agent`. A role-play inside one thread is not a worker.
11. Cross-agent communication must use `SendMessage`. Hidden side channels are forbidden.
12. The user must be able to inspect every agent dialogue. The final report must provide thread references.
13. External AI requests and responses must be stored in the run dialogue directory.
14. Secrets must come from environment variables and must never be written into the Skill or transcript.
15. External AI members (Codex, MCP, HTTP API) execute tasks through their respective adapters. The dispatcher must record which adapter was used and any failures.
16. Every real agent must have its own visible WorkBuddy dialogue thread. The dispatcher must not simulate an agent with role-play inside its own response.
