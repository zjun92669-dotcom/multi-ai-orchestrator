#!/usr/bin/env python3
"""
Reproducible Random Task Assignment

Assigns simple, homogeneous, independent sub-tasks to qualified agents
using a recorded random seed for reproducibility.

Usage:
    python random_assign.py --tasks <task_list_json> [--seed <seed_value>] [--agents <agent_list_json>]

Examples:
    python random_assign.py --tasks '[{"id":"T-1","type":"format"},{"id":"T-2","type":"format"}]' --seed 42
    python random_assign.py --tasks tasks.json --agents agents.json --seed 20261106

Input:
    --tasks: JSON file path or JSON string. Each task must have:
        - id: unique task identifier (string)
        - type: task category (string, used for homogeneity check)
        - description: what the task involves (string)
    --agents: JSON file path or JSON string. Each agent must have:
        - id: unique agent identifier (string)
        - capabilities: list of task types this agent can handle (list of strings)
    --seed: Optional integer seed. If omitted, generates from current timestamp.

Output (stdout):
    JSON object with:
        - assignments: list of {task_id, agent_id} pairs
        - seed: the seed value used (integer)
        - timestamp: ISO 8601 timestamp of assignment

Exit codes:
    0: success
    1: invalid input
    2: no qualified agents for a task
"""

import sys
import json
import argparse
import random
from datetime import datetime, timezone


def load_json_arg(arg_value):
    """Load JSON from file path or inline JSON string."""
    if arg_value is None:
        return None
    # Try parsing as inline JSON first
    try:
        return json.loads(arg_value)
    except json.JSONDecodeError:
        # Try reading as file
        try:
            with open(arg_value, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error: cannot parse JSON argument: {e}", file=sys.stderr)
            sys.exit(1)


def validate_tasks(tasks):
    """Validate task list structure."""
    if not isinstance(tasks, list) or len(tasks) == 0:
        print("Error: tasks must be a non-empty list", file=sys.stderr)
        sys.exit(1)

    for task in tasks:
        if not isinstance(task, dict):
            print(f"Error: task must be a dict, got {type(task)}", file=sys.stderr)
            sys.exit(1)
        if 'id' not in task or 'type' not in task:
            print(f"Error: task missing required field 'id' or 'type': {task}", file=sys.stderr)
            sys.exit(1)

    # Check homogeneity: all tasks must have the same type
    types = set(t['type'] for t in tasks)
    if len(types) > 1:
        print(f"Error: tasks are not homogeneous. Found types: {types}", file=sys.stderr)
        print("Random assignment only applies to tasks of the same type.", file=sys.stderr)
        sys.exit(1)


def validate_agents(agents):
    """Validate agent list structure."""
    if not isinstance(agents, list) or len(agents) == 0:
        print("Error: agents must be a non-empty list", file=sys.stderr)
        sys.exit(1)

    for agent in agents:
        if not isinstance(agent, dict):
            print(f"Error: agent must be a dict, got {type(agent)}", file=sys.stderr)
            sys.exit(1)
        if 'id' not in agent or 'capabilities' not in agent:
            print(f"Error: agent missing required field 'id' or 'capabilities': {agent}", file=sys.stderr)
            sys.exit(1)


def filter_qualified_agents(task_type, agents):
    """Return only agents whose capabilities include the task type."""
    qualified = [a for a in agents if task_type in a.get('capabilities', [])]
    return qualified


def assign_tasks(tasks, agents, seed):
    """
    Assign tasks to qualified agents using a seeded random shuffle.

    Algorithm:
    1. Filter agents qualified for the task type.
    2. Shuffle the qualified agent list using the seed.
    3. Assign tasks round-robin to shuffled agents.

    This ensures:
    - Reproducibility: same seed + same input = same output
    - Fairness: tasks distributed evenly among qualified agents
    - Randomness: agent order is randomized per seed
    """
    rng = random.Random(seed)

    task_type = tasks[0]['type']
    qualified = filter_qualified_agents(task_type, agents)

    if len(qualified) == 0:
        print(f"Error: no qualified agents for task type '{task_type}'", file=sys.stderr)
        sys.exit(2)

    # Shuffle qualified agents
    shuffled_agents = list(qualified)
    rng.shuffle(shuffled_agents)

    # Round-robin assignment
    assignments = []
    for i, task in enumerate(tasks):
        agent = shuffled_agents[i % len(shuffled_agents)]
        assignments.append({
            'task_id': task['id'],
            'agent_id': agent['id'],
            'task_type': task_type
        })

    return assignments


def main():
    parser = argparse.ArgumentParser(
        description='Reproducible random task assignment for multi-AI orchestrator'
    )
    parser.add_argument(
        '--tasks',
        required=True,
        help='JSON file path or inline JSON string of task list'
    )
    parser.add_argument(
        '--agents',
        required=False,
        help='JSON file path or inline JSON string of agent list. If omitted, uses default 3 agents.'
    )
    parser.add_argument(
        '--seed',
        type=int,
        required=False,
        default=None,
        help='Integer seed for reproducible assignment. If omitted, generated from timestamp.'
    )

    args = parser.parse_args()

    # Load and validate tasks
    tasks = load_json_arg(args.tasks)
    validate_tasks(tasks)

    # Load agents (default: 3 fixed agents)
    if args.agents:
        agents = load_json_arg(args.agents)
    else:
        agents = [
            {'id': 'research-agent', 'capabilities': ['research', 'read', 'analyze', 'general_simple']},
            {'id': 'execution-agent', 'capabilities': ['write', 'execute', 'format', 'generate', 'general_simple']},
            {'id': 'qa-agent', 'capabilities': ['verify', 'review', 'check', 'general_simple']}
        ]
    validate_agents(agents)

    # Generate or use seed
    if args.seed is not None:
        seed = args.seed
    else:
        seed = int(datetime.now(timezone.utc).timestamp() * 1000)

    # Assign tasks
    assignments = assign_tasks(tasks, agents, seed)

    # Output result
    result = {
        'assignments': assignments,
        'seed': seed,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'task_count': len(tasks),
        'agent_count': len(agents),
        'qualified_agent_count': len(filter_qualified_agents(tasks[0]['type'], agents))
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
