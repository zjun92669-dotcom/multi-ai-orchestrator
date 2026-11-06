#!/usr/bin/env python3
"""Call one external AI agent through a declarative CLI or HTTP adapter."""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib import error, request


ENV_PATTERN = re.compile(r"^\$\{([A-Z_][A-Z0-9_]*)\}$")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def expand_env(value):
    if not isinstance(value, str):
        return value
    match = ENV_PATTERN.match(value)
    if not match:
        return value
    env_name = match.group(1)
    if env_name not in os.environ:
        raise ValueError(f"Missing environment variable: {env_name}")
    return os.environ[env_name]


def load_config(path):
    with open(path, "r", encoding="utf-8") as handle:
        config = json.load(handle)
    if not isinstance(config, dict) or not isinstance(config.get("agents"), dict):
        raise ValueError("Adapter config must contain an agents object")
    return config


def append_trace(path, record):
    if not path:
        return
    trace_path = Path(path)
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    with trace_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def run_cli(agent_id, spec, message):
    command = spec.get("command")
    if not isinstance(command, list) or not command or not all(
        isinstance(item, str) and item for item in command
    ):
        raise ValueError("CLI adapter requires a non-empty command array")
    expanded = [expand_env(item) for item in command]
    child_env = os.environ.copy()
    for key, value in (spec.get("env") or {}).items():
        child_env[key] = str(expand_env(value))
    timeout = int(spec.get("timeout_seconds", 600))
    payload = json.dumps(message, ensure_ascii=False)
    cwd_value = spec.get("cwd")
    cwd = expand_env(cwd_value) if cwd_value else None
    completed = subprocess.run(
        expanded,
        input=payload,
        text=True,
        encoding="utf-8",
        capture_output=True,
        cwd=cwd,
        env=child_env,
        timeout=timeout,
        shell=False,
    )
    return {
        "status": "completed" if completed.returncode == 0 else "failed",
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "agent_id": agent_id,
    }


def run_http(agent_id, spec, message):
    url = expand_env(spec.get("url"))
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        raise ValueError("HTTP adapter requires an http or https url")
    headers = {"content-type": "application/json"}
    for key, value in (spec.get("headers") or {}).items():
        headers[key] = str(expand_env(value))
    body = json.dumps(message, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers=headers,
        method=spec.get("method", "POST").upper(),
    )
    timeout = int(spec.get("timeout_seconds", 600))
    try:
        with request.urlopen(req, timeout=timeout) as response:
            text = response.read().decode("utf-8", errors="replace")
            status = response.status
    except error.HTTPError as failure:
        text = failure.read().decode("utf-8", errors="replace")
        return {
            "status": "failed",
            "http_status": failure.code,
            "response": text,
            "agent_id": agent_id,
        }
    return {
        "status": "completed" if 200 <= status < 300 else "failed",
        "http_status": status,
        "response": text,
        "agent_id": agent_id,
    }


def main():
    parser = argparse.ArgumentParser(description="Call one external AI agent")
    parser.add_argument("--config", required=True)
    parser.add_argument("--agent", required=True)
    parser.add_argument("--message", required=True)
    parser.add_argument("--dialogue")
    args = parser.parse_args()

    started = time.time()
    record = {
        "timestamp": now_iso(),
        "agent_id": args.agent,
        "input": args.message,
    }
    try:
        message = json.loads(args.message)
        if not isinstance(message, dict):
            raise ValueError("Message must be a JSON object")
        config = load_config(args.config)
        spec = config["agents"].get(args.agent)
        if not isinstance(spec, dict):
            raise ValueError(f"Unknown external agent: {args.agent}")
        transport = spec.get("transport")
        if transport == "cli":
            result = run_cli(args.agent, spec, message)
        elif transport == "http":
            result = run_http(args.agent, spec, message)
        else:
            raise ValueError("transport must be cli or http")
        record["result"] = result
        record["elapsed_ms"] = round((time.time() - started) * 1000)
        append_trace(args.dialogue, record)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if result.get("status") == "completed" else 3)
    except subprocess.TimeoutExpired as failure:
        record["error"] = {"code": "TIMEOUT", "message": str(failure)}
        append_trace(args.dialogue, record)
        print(json.dumps(record, ensure_ascii=False, indent=2))
        sys.exit(124)
    except Exception as failure:
        record["error"] = {
            "code": "ADAPTER_ERROR",
            "message": str(failure),
        }
        append_trace(args.dialogue, record)
        print(json.dumps(record, ensure_ascii=False, indent=2))
        sys.exit(4)


if __name__ == "__main__":
    main()
