#!/usr/bin/env python3
import asyncio
import sys
import structlog
import uvicorn

logger = structlog.get_logger()

COMMANDS = {
    "start": "Start the Hermes API server",
    "status": "Show Hermes orchestrator status",
    "run-agent": "Run a specific agent by ID",
    "run-pipeline": "Run a specific pipeline by name",
    "list-agents": "List all registered agents",
    "list-pipelines": "List all registered pipelines",
    "health": "Check all service health",
}


def cmd_start(args):
    host = getattr(args, "host", "0.0.0.0")
    port = getattr(args, "port", 8101)
    reload = getattr(args, "reload", False)
    logger.info("hermes_starting", host=host, port=port)
    uvicorn.run("hermes.api:app", host=host, port=port, reload=reload, log_level="info")


async def cmd_status(args):
    from hermes.orchestrator import get_hermes
    h = get_hermes()
    await h.initialize()
    s = h.get_status()
    print(f"Hermes Orchestrator — {s['status']}")
    print(f"  Agents: {len(s['agents'])} registered")
    print(f"  Pipelines: {len(s['pipelines'])} defined")
    print(f"  Event Bus: {s['event_bus']['total_events']} events processed")
    print(f"  Scheduler: {'running' if s['scheduler_running'] else 'stopped'}")
    print()
    print("Agents:")
    for a in s["agents"]:
        print(f"  [{a['status']:>8}] {a['id']} — {a['name']}")
    print()
    print("Pipelines:")
    for p in s["pipelines"]:
        print(f"  - {p}")


async def cmd_run_agent(args):
    from hermes.orchestrator import get_hermes
    h = get_hermes()
    await h.initialize()
    try:
        result = await h.run_agent(args.agent_id)
        print(f"Run {result['run_id']}: {result['status']}")
        if result["error"]:
            print(f"  Error: {result['error']}")
        else:
            print(f"  Result: {str(result['result'])[:300]}")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


async def cmd_run_pipeline(args):
    from hermes.orchestrator import get_hermes
    h = get_hermes()
    await h.initialize()
    try:
        result = await h.run_pipeline(args.pipeline_name)
        print(f"Pipeline '{args.pipeline_name}': {len(result['steps'])} steps")
        for s in result["steps"]:
            print(f"  [{s['status']:>8}] {s['agent']} — {s.get('run_id', 'N/A')}")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


async def cmd_list_agents(args):
    from hermes.orchestrator import get_hermes
    h = get_hermes()
    await h.initialize()
    print(f"{'STATUS':>8}  {'ID':<16}  NAME")
    print("-" * 60)
    for a in h.get_status()["agents"]:
        print(f"{a['status']:>8}  {a['id']:<16}  {a['name']}")


async def cmd_list_pipelines(args):
    from hermes.orchestrator import get_hermes
    h = get_hermes()
    await h.initialize()
    print("Registered Pipelines:")
    for p in h.get_status()["pipelines"]:
        print(f"  - {p}")


async def cmd_health(args):
    import httpx
    from hermes.config import settings
    services = {
        "hermes": f"http://localhost:{settings.port}/health",
        "governor": "http://localhost:8100/health",
    }
    print(f"{'SERVICE':<16}  STATUS  VERSION")
    print("-" * 50)
    for name, url in services.items():
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(url)
                if r.status_code == 200:
                    data = r.json()
                    print(f"{name:<16}  OK      {data.get('version', data.get('service', '?'))}")
                else:
                    print(f"{name:<16}  FAIL    HTTP {r.status_code}")
        except Exception as e:
            print(f"{name:<16}  DOWN    {str(e)[:40]}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Hermes Multi-Agent Orchestrator CLI")
    parser.add_argument("command", nargs="?", default="start", choices=list(COMMANDS.keys()),
        help="Command to run (default: start)")
    parser.add_argument("--host", default="0.0.0.0", help="API server host")
    parser.add_argument("--port", type=int, default=8101, help="API server port")
    parser.add_argument("--reload", action="store_true", help="Auto-reload on file changes")
    parser.add_argument("agent_id", nargs="?", help="Agent ID for run-agent command")
    parser.add_argument("pipeline_name", nargs="?", help="Pipeline name for run-pipeline command")

    args = parser.parse_args()

    cmd_map = {
        "start": cmd_start,
        "status": cmd_status,
        "run-agent": cmd_run_agent,
        "run-pipeline": cmd_run_pipeline,
        "list-agents": cmd_list_agents,
        "list-pipelines": cmd_list_pipelines,
        "health": cmd_health,
    }

    cmd = cmd_map.get(args.command)
    if cmd is None:
        print(f"Unknown command: {args.command}")
        print(f"Available: {', '.join(COMMANDS.keys())}")
        sys.exit(1)

    if asyncio.iscoroutinefunction(cmd):
        asyncio.run(cmd(args))
    else:
        cmd(args)


if __name__ == "__main__":
    main()