#!/usr/bin/env python3
"""Assign task tickets to native or external agents with a selected strategy."""

import argparse
import json
import random
import sys
from datetime import datetime, timezone


VALID_STRATEGIES = {
    "round_robin",
    "random",
    "least_load",
    "capability_score",
    "external_first",
}


def load_json(value):
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        with open(value, "r", encoding="utf-8") as handle:
            return json.load(handle)


def normalized_capabilities(agent):
    values = agent.get("capabilities", [])
    if not isinstance(values, list):
        raise ValueError(f"Agent {agent.get('agent_id')} capabilities must be a list")
    return {str(value) for value in values}


def qualified_agents(task, agents):
    required = task.get("required_capability") or task.get("type")
    if not required:
        return list(agents)
    return [
        agent
        for agent in agents
        if str(required) in normalized_capabilities(agent)
    ]


def capability_score(task, agent):
    required = str(task.get("required_capability") or task.get("type") or "")
    scores = agent.get("capability_scores") or {}
    if required and isinstance(scores, dict):
        value = scores.get(required)
        if isinstance(value, (int, float)):
            return float(value)
    return float(agent.get("default_score", 1))


def choose_agent(task, agents, strategy, rng, cursor, loads):
    candidates = qualified_agents(task, agents)
    if not candidates:
        return None

    if strategy == "random":
        return rng.choice(candidates)

    if strategy == "least_load":
        return min(
            candidates,
            key=lambda agent: (
                loads[agent["agent_id"]],
                -capability_score(task, agent),
                agent["agent_id"],
            ),
        )

    if strategy == "capability_score":
        return max(
            candidates,
            key=lambda agent: (
                capability_score(task, agent),
                -loads[agent["agent_id"]],
                agent["agent_id"],
            ),
        )

    if strategy == "external_first":
        external = [
            agent
            for agent in candidates
            if str(agent.get("kind", "workbuddy")).startswith("external_")
        ]
        pool = external or candidates
        start = cursor[0] % len(pool)
        selected = pool[start]
        cursor[0] += 1
        return selected

    start = cursor[0] % len(candidates)
    selected = candidates[start]
    cursor[0] += 1
    return selected


def assign(tasks, agents, strategy, seed):
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("tasks must be a non-empty list")
    if not isinstance(agents, list) or not agents:
        raise ValueError("agents must be a non-empty list")
    if strategy not in VALID_STRATEGIES:
        raise ValueError(
            f"strategy must be one of: {', '.join(sorted(VALID_STRATEGIES))}"
        )

    normalized_agents = []
    seen_agents = set()
    for agent in agents:
        if not isinstance(agent, dict):
            raise ValueError("Every agent must be an object")
        agent_id = agent.get("agent_id")
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("Every agent requires a non-empty agent_id")
        if agent_id in seen_agents:
            raise ValueError(f"Duplicate agent_id: {agent_id}")
        seen_agents.add(agent_id)
        normalized_agents.append(agent)

    ordered_tasks = sorted(
        tasks,
        key=lambda task: (-int(task.get("priority", 0)), str(task.get("id", ""))),
    )
    rng = random.Random(seed)
    cursor = [0]
    loads = {
        agent["agent_id"]: int(agent.get("load", 0))
        for agent in normalized_agents
    }
    assignments = []
    unassigned = []

    for task in ordered_tasks:
        task_id = task.get("id")
        if not isinstance(task_id, str) or not task_id:
            raise ValueError("Every task requires a non-empty id")
        selected = choose_agent(
            task, normalized_agents, strategy, rng, cursor, loads
        )
        if selected is None:
            unassigned.append(
                {
                    "task_id": task_id,
                    "reason": "NO_QUALIFIED_AGENT",
                    "required_capability": task.get("required_capability")
                    or task.get("type"),
                }
            )
            continue
        loads[selected["agent_id"]] += 1
        assignments.append(
            {
                "task_id": task_id,
                "agent_id": selected["agent_id"],
                "agent_kind": selected.get("kind", "workbuddy"),
                "strategy": strategy,
                "score": capability_score(task, selected),
                "load_after_assignment": loads[selected["agent_id"]],
            }
        )

    return {
        "strategy": strategy,
        "seed": seed,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "task_count": len(tasks),
        "agent_count": len(normalized_agents),
        "assignments": assignments,
        "unassigned": unassigned,
    }


def main():
    parser = argparse.ArgumentParser(description="Assign tasks to AI agents")
    parser.add_argument("--tasks", required=True, help="JSON file path or JSON array")
    parser.add_argument("--agents", required=True, help="JSON file path or JSON array")
    parser.add_argument("--strategy", default="capability_score")
    parser.add_argument("--seed", type=int)
    args = parser.parse_args()

    seed = args.seed
    if seed is None:
        seed = int(datetime.now(timezone.utc).timestamp() * 1000)
    try:
        result = assign(
            load_json(args.tasks),
            load_json(args.agents),
            args.strategy,
            seed,
        )
    except (OSError, ValueError, json.JSONDecodeError) as failure:
        print(json.dumps({"error": str(failure)}, ensure_ascii=False, indent=2))
        sys.exit(1)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(2 if result["unassigned"] else 0)


if __name__ == "__main__":
    main()
