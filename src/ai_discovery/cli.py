"""Operational CLI: run a lane locally without the Dagster UI."""

from __future__ import annotations

import argparse
import json
import sys

from .db import session_scope
from .ingest import ingest_all, run_discovery_lane, run_registry_lane, upsert_sources
from .registry import load_sources_config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ai-discovery-ingest")
    parser.add_argument("lane", choices=["registry", "discovery", "all"])
    parser.add_argument("--source", action="append", dest="sources")
    parser.add_argument("--provider", action="append", dest="providers")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--max-per-query", type=int, default=10)
    args = parser.parse_args(argv)

    config = load_sources_config()
    payload: dict = {}
    with session_scope() as session:
        upsert_sources(session, config)
        session.flush()
        if args.lane == "all":
            # One reactor cycle for both lanes (Twisted reactors cannot restart).
            payload.update(
                ingest_all(
                    session,
                    config,
                    source_ids=args.sources,
                    limit=args.limit,
                    max_per_query=args.max_per_query,
                )
            )
        elif args.lane == "registry":
            payload["registry"] = run_registry_lane(
                session, config, source_ids=args.sources, limit=args.limit
            ).as_dict()
        else:
            payload["discovery"] = run_discovery_lane(
                session, config, providers=args.providers, max_per_query=args.max_per_query
            ).as_dict()
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
