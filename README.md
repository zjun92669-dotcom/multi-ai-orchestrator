# Multi-AI Orchestrator

A WorkBuddy skill for visible multi-agent teams with recursive supervision, native Agent and SendMessage communication, transcript audit, external CLI and HTTP AI adapters, verification, and two-way Codex handoff.

## Features

- **Visible team hierarchy**: User > Dispatcher > Research / Execution / QA agents, with optional recursive child agents
- **Role-based tool isolation**: Research (read-only), Execution (write to specified paths), QA (read-only verification)
- **Multi-strategy dispatch**: round-robin, random, least-load, capability-score, external-first
- **QA verification loop**: up to 2 fix-verify rounds per failed sub-task
- **External AI integration**: CLI adapter (Codex) and HTTP adapter for any JSON API
- **Codex background sync**: two-way handoff between Codex and WorkBuddy

## Installation

### WorkBuddy UI (preferred)

1. Open "Expert - Skill - Connector" in WorkBuddy desktop
2. Choose "Add Skill" > "Upload Skill"
3. Select the ZIP file
4. Enable "Non-high-risk auto install"
5. Confirm the security scan

### Manual

- User-level: copy to `~/.workbuddy-ai/skills/multi-ai-orchestrator/`
- Project-level: copy to `.workbuddy-ai/skills/multi-ai-orchestrator/`

## Requirements

- WorkBuddy desktop (Agent, SendMessage, TaskOutput, TeamCreate tools)
- Python 3.8+ (for dispatch_engine.py, task_validator.py, and other scripts)

## Usage

Activate this skill when you need multi-agent task decomposition:

- "Launch multi-AI dispatch"
- "Split work among three AIs"
- "Assign research, execution, and QA agents"

The dispatcher decomposes your request into sub-tasks, presents a work breakdown for confirmation, then launches agents in parallel.

## Structure

```
multi-ai-orchestrator/
  SKILL.md              Skill definition and workflow
  LICENSE               MIT License
  .gitignore
  .codebuddy-plugin/
    plugin.json         Plugin metadata
  scripts/
    dispatch_engine.py        Multi-strategy assignment engine
    random_assign.py          Legacy random assignment
    task_validator.py         Task ticket validator
    team_manifest_validator.py  Hierarchy manifest validator
    external_agent_adapter.py   External AI CLI/HTTP adapter
  references/
    agent_profiles.md          Role definitions and prompt templates
    task_templates.md          Task ticket format and decomposition rules
    failure_handling.md        Failure protocol (L1-L4)
    team-communication.md      Agent tree and messaging protocol
    external-ai-integration.md External AI registry and adapters
    codex-background-sync.md   Codex two-way handoff
    distribution-and-license.md  License and distribution guide
    workbuddy-video-guidelines.md  Skill design best practices
  assets/
    report_template.md         Final report template
    team_manifest.example.json  Example hierarchy
    external_agents.example.json  Example external AI registry
```

## License

MIT License. See [LICENSE](LICENSE) for details.

Copyright (c) 2026 multi-ai-orchestrator contributors
