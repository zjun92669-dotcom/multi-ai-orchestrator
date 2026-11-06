#!/usr/bin/env python3
"""Validate a WorkBuddy multi-agent hierarchy manifest."""

import argparse
import json
import sys


TERMINAL_STATUS = {"idle", "running", "waiting", "completed", "failed", "cancelled"}


def load_manifest(value):
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        with open(value, "r", encoding="utf-8") as handle:
            return json.load(handle)


def validate(manifest):
    errors = []
    warnings = []

    if not isinstance(manifest, dict):
        return ["Manifest must be a JSON object"], warnings

    for field in ("trace_id", "team_name", "root_supervisor", "agents"):
        if field not in manifest:
            errors.append(f"Missing required field: {field}")
    if errors:
        return errors, warnings

    agents = manifest["agents"]
    if not isinstance(agents, list) or not agents:
        return ["agents must be a non-empty list"], warnings

    by_id = {}
    by_name = {}
    for index, agent in enumerate(agents):
        if not isinstance(agent, dict):
            errors.append(f"Agent at index {index} is not an object")
            continue
        for field in (
            "agent_id",
            "name",
            "role",
            "supervisor_id",
            "thread_ref",
            "status",
        ):
            value = agent.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"Agent at index {index} has invalid {field}")
        agent_id = agent.get("agent_id")
        name = agent.get("name")
        if isinstance(agent_id, str):
            if agent_id in by_id:
                errors.append(f"Duplicate agent_id: {agent_id}")
            by_id[agent_id] = agent
        if isinstance(name, str):
            if name in by_name:
                errors.append(f"Duplicate agent name: {name}")
            by_name[name] = agent
        if agent.get("status") not in TERMINAL_STATUS:
            errors.append(
                f"Agent {agent_id or index} has invalid status: {agent.get('status')}"
            )

    root = manifest.get("root_supervisor")
    if root not in by_name:
        errors.append(f"root_supervisor does not match any agent name: {root}")

    for agent_id, agent in by_id.items():
        supervisor = agent.get("supervisor_id")
        if agent.get("name") == root:
            if supervisor != "user":
                errors.append(f"Root supervisor {agent_id} must report to user")
            continue
        if supervisor != "user" and supervisor not in by_name:
            errors.append(
                f"Agent {agent_id} has unknown supervisor_id: {supervisor}"
            )

    def walk(agent_id, visiting, visited):
        if agent_id in visiting:
            return True
        if agent_id in visited:
            return False
        visiting.add(agent_id)
        agent = by_id.get(agent_id)
        if agent:
            supervisor = agent.get("supervisor_id")
            if supervisor in by_name:
                supervisor_id = by_name[supervisor].get("agent_id")
                if walk(supervisor_id, visiting, visited):
                    return True
        visiting.remove(agent_id)
        visited.add(agent_id)
        return False

    visited = set()
    for agent_id in by_id:
        if walk(agent_id, set(), visited):
            errors.append(f"Reporting cycle detected at agent: {agent_id}")
            break

    if len(by_id) < 2:
        warnings.append("Manifest has fewer than two agents")

    return errors, warnings


def main():
    parser = argparse.ArgumentParser(
        description="Validate a WorkBuddy team hierarchy manifest"
    )
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()

    try:
        manifest = load_manifest(args.manifest)
    except (OSError, json.JSONDecodeError) as error:
        print(json.dumps({"valid": False, "errors": [str(error)], "warnings": []}))
        sys.exit(1)

    errors, warnings = validate(manifest)
    print(
        json.dumps(
            {"valid": not errors, "errors": errors, "warnings": warnings},
            indent=2,
            ensure_ascii=False,
        )
    )
    sys.exit(0 if not errors else 2)


if __name__ == "__main__":
    main()
