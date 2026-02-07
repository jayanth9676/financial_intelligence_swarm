"""Orchestrate loading data into all databases."""

import argparse
import sys

from backend.loaders import load_graph, load_memory, load_vectors


def main():
    """Main entry point for data loading."""
    parser = argparse.ArgumentParser(description="Load data into FIS databases")
    parser.add_argument(
        "--target",
        choices=["all", "graph", "vectors", "memory"],
        default="all",
        help="Which database to load (default: all)",
    )
    parser.add_argument(
        "--skip-errors",
        action="store_true",
        help="Continue loading other databases if one fails",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("FINANCIAL INTELLIGENCE SWARM - DATA LOADER")
    print("=" * 60)

    loaders = {
        "graph": ("Neo4j Graph Database", load_graph),
        "vectors": ("Qdrant Vector Store", load_vectors),
        "memory": ("Mem0 Agent Memory", load_memory),
    }

    targets = list(loaders.keys()) if args.target == "all" else [args.target]
    results = {}

    for target in targets:
        name, loader_func = loaders[target]
        print(f"\n{'=' * 60}")
        print(f"Loading: {name}")
        print("=" * 60)

        try:
            loader_func()
            results[target] = "SUCCESS"
        except Exception as e:
            results[target] = f"FAILED: {e}"
            print(f"\nError loading {name}: {e}")

            if not args.skip_errors:
                print("\nUse --skip-errors to continue loading other databases")
                sys.exit(1)

    print("\n" + "=" * 60)
    print("LOADING SUMMARY")
    print("=" * 60)

    for target, status in results.items():
        name, _ = loaders[target]
        status_icon = "✓" if status == "SUCCESS" else "✗"
        print(f"  {status_icon} {name}: {status}")

    failed = sum(1 for s in results.values() if s != "SUCCESS")
    if failed > 0:
        print(f"\n{failed} loader(s) failed")
        sys.exit(1)
    else:
        print("\nAll loaders completed successfully!")


if __name__ == "__main__":
    main()
