# Failure Handling Protocol

## Overview

The multi-AI orchestrator handles failures at four levels. Each level has specific triggers, actions, and escalation paths.

## Level 1: Sub-Agent Timeout or Crash

### Trigger
- An Agent invocation does not return within the timeout period (default: 120 seconds).
- An Agent returns an error or empty result indicating a crash.
- `TeamCreate` fails and no visible team can be created.
- `Agent` fails and no independent worker thread exists.

### Action

```
1. Record the failure: {agent_name, task_id, failure_type, timestamp}
2. Retry the same task with a fresh Agent invocation.
3. If the retry also fails:
   a. Mark the task as "failed" in the task ledger.
   b. Log the failure reason.
   c. Continue with other independent tasks.
   d. Skip any tasks that depend on the failed task.
4. In the final report, include all Level 1 failures with details.
```

If the native `Agent` tool is unavailable, mark the branch blocked with reason `NATIVE_AGENT_TOOLS_UNAVAILABLE`. Do not replace the worker with a simulated role-play.

### Decision Tree

```
Agent timeout/crash detected
├── Retry count < 1?
│   ├── Yes → Launch fresh Agent for the same task. Increment retry count.
│   └── No  → Mark task as failed. Log details. Continue other tasks.
│            └── Any tasks depend on this one?
│                ├── Yes → Mark dependent tasks as "blocked" (skipped).
│                └── No  → Proceed normally.
```

---

## Level 2: QA Rejection

### Trigger
- The QA Agent returns a report with status "fail".
- The QA Agent identifies defects in the Execution Agent's output.

### Action

```
1. Extract the defect list from the QA report.
2. Send the defects to the Execution Agent via SendMessage:
   "QA Agent identified the following defects in your output for task {task_id}:
    {defect_list}
    Please fix these issues and resubmit."
3. Wait for the Execution Agent to complete fixes.
4. Re-launch the QA Agent to verify the fixed output.
5. If QA still fails after 2 rounds of fix-verify:
   a. Mark the task as "failed (qa_rejection)".
   b. Include the unresolved defects in the final report.
   c. Continue with other tasks.
```

### Decision Tree

```
QA Agent returns "fail"
├── Fix-verify round < 2?
│   ├── Yes → Send defects to Execution Agent. Wait for fix. Re-run QA. Increment round.
│   └── No  → Mark task as "failed (qa_rejection)". Log unresolved defects. Continue.
```

### Defect Severity Classification

| Severity | Description | Action |
|----------|-------------|--------|
| Critical | Output is missing, empty, or fundamentally wrong | Must fix before any further work |
| Major | Output exists but has significant issues (wrong format, missing key sections) | Must fix before QA can pass |
| Minor | Output is mostly correct but has small issues (typos, formatting) | Fix recommended but does not block pass |

The QA Agent classifies each defect with a severity level. The dispatcher includes all defects in the fix message to the Execution Agent.

The revision request and the corrected result must both use `SendMessage`. The messages remain in the visible worker and dispatcher threads.

---

## Level 3: Overall Task Cannot Complete

### Trigger
- One or more Level 1 or Level 2 failures prevent the overall task from being completed.
- The dispatcher determines that remaining tasks cannot proceed without the failed tasks.

### Action

```
1. Identify all completed, failed, and blocked tasks.
2. For completed tasks: collect their outputs.
3. For failed tasks: collect failure reasons and details.
4. For blocked tasks: note which failure caused the block.
5. Generate the final report using assets/report_template.md.
6. Present the report to the user with:
   - What was accomplished
   - What failed and why
   - What was blocked and by what
   - Recommended next steps
```

### Decision Tree

```
Assess overall task status
├── All tasks completed and QA passed?
│   ├── Yes → Generate success report. Present to user.
│   └── No  → Assess impact of failures
│       ├── Can remaining tasks proceed independently?
│       │   ├── Yes → Continue with remaining tasks. Generate partial report.
│       │   └── No  → Stop execution. Generate failure report with recommendations.
```

---

## Level 4: External AI Execution Failure

### Trigger
- An external AI adapter (Codex CLI, MCP server, or HTTP API) returns an error, timeout, or empty result.
- The external AI response does not satisfy the acceptance criteria.
- The adapter itself crashes or fails to connect.

### Action

```
1. Record the failure: {agent_name, task_id, adapter_type, external_ai_id, failure_type, timestamp}
2. Retry the same task through the adapter once.
3. If the retry also fails:
   a. Check if an internal agent can handle the task as fallback.
   b. If internal fallback is possible: re-assign to an internal Execution agent.
   c. If no internal fallback: mark the task as "failed (external)" in the task ledger.
   d. Log the failure reason and adapter response.
   e. Continue with other independent tasks.
   f. Skip any tasks that depend on the failed task.
4. In the final report, include all Level 4 failures with adapter details.
```

### Decision Tree

```
External AI adapter failure detected
├── Retry count < 1?
│   ├── Yes → Resubmit task through adapter. Increment retry count.
│   └── No  → Can internal agent handle this task?
│       ├── Yes → Re-assign to internal Execution agent. Log fallback.
│       └── No  → Mark task as failed (external). Log details. Continue other tasks.
│                └── Any tasks depend on this one?
│                    ├── Yes → Mark dependent tasks as "blocked" (skipped).
│                    └── No  → Proceed normally.
```

### Adapter-Specific Failure Modes

| Adapter | Common Failures | Detection |
|---------|----------------|-----------|
| Codex CLI | Process timeout, exit code nonzero, empty stdout | Check exit code AND output content |
| MCP Server | Tool call error, no response, invalid JSON | Check tool response status and content |
| HTTP API | Connection refused, HTTP 5xx, timeout, empty body | Check HTTP status code AND response body |

The dispatcher must verify the actual output content. A successful exit code or HTTP 200 does not satisfy the acceptance criteria if the content is empty or wrong.

---

## Tool Restriction Violation Handling

### Trigger
- The dispatcher detects that a sub-agent used a tool outside its permitted set (e.g., Research Agent used Write).

### Action

```
1. Log the violation: {agent_name, task_id, tool_used, permitted_tools, timestamp}
2. Mark the task as "violation" in the task ledger.
3. Discard any output produced by the violating action.
4. Re-run the task with a fresh Agent invocation.
5. If the violation recurs:
   a. Mark the task as "failed (violation)".
   b. Include the violation details in the final report.
   c. Recommend upgrading to hard constraint (Expert system) in the report.
```

---

## Recovery Procedures

### Procedure A: Re-launch After Timeout

```python
# Pseudocode for retry logic
def handle_timeout(task, retry_count):
    if retry_count < 1:
        log("TIMEOUT", task.id, "retrying")
        launch_agent(task, retry=True)
    else:
        log("TIMEOUT", task.id, "max retries reached, marking failed")
        task.status = "failed"
        task.failure_reason = "timeout_after_retry"
        block_dependents(task.id)
```

### Procedure B: Fix-Verify Cycle

```python
# Pseudocode for QA rejection cycle
def handle_qa_rejection(task, qa_report, fix_round):
    if fix_round < 2:
        log("QA_REJECT", task.id, f"round {fix_round}")
        send_message(
            to=task.assigned_agent,
            message=format_defects(qa_report.defects)
        )
        wait_for_fix(task)
        re_run_qa(task)
    else:
        log("QA_REJECT", task.id, "max rounds reached, marking failed")
        task.status = "failed"
        task.failure_reason = "qa_rejection_after_2_rounds"
        task.unresolved_defects = qa_report.defects
```

### Procedure C: Cascading Failure

```python
# Pseudocode for handling blocked tasks
def block_dependents(failed_task_id):
    for task in all_tasks:
        if failed_task_id in task.dependencies:
            task.status = "blocked"
            task.blocked_by = failed_task_id
            log("BLOCKED", task.id, f"by {failed_task_id}")
            # Recursively block dependents of dependents
            block_dependents(task.id)
```

### Procedure D: External AI Retry and Fallback

```python
# Pseudocode for external AI failure handling
def handle_external_failure(task, adapter_response, retry_count):
    if retry_count < 1:
        log("L4_EXTERNAL", task.id, "retrying via adapter")
        resubmit_via_adapter(task, retry=True)
    else:
        # Try internal fallback
        if can_internal_agent_handle(task):
            log("L4_EXTERNAL", task.id, "falling back to internal agent")
            reassign_to_internal(task)
        else:
            log("L4_EXTERNAL", task.id, "no fallback, marking failed")
            task.status = "failed"
            task.failure_reason = "external_ai_failure_after_retry"
            task.adapter_response = adapter_response
            block_dependents(task.id)
```

---

## Failure Logging Format

All failures must be logged in the following format:

```json
{
  "timestamp": "2026-11-06T15:30:00Z",
  "level": "L1",
  "agent_name": "execution-agent",
  "task_id": "T-3",
  "failure_type": "timeout",
  "details": "Agent did not return within 120 seconds",
  "retry_count": 1,
  "resolution": "marked_as_failed"
}
```

The dispatcher collects all failure logs and includes them in the final report under the "Failures and Issues" section.
