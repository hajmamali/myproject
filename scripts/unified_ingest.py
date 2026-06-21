#!/usr/bin/env python3
"""
Unified Ingestion CLI
=====================
Command-line interface for the "Unified Loader" (The Missing Link).

Usage:
    python scripts/unified_ingest.py --file /path/to/contract.pdf

Features:
- Validates file existence
- Runs full ingestion pipeline (Text -> Vector -> Graph -> Sync)
- Reports detailed status for each stage
"""

import sys
import asyncio
import logging
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mahoun.orchestrator.unified_loader import UnifiedLoader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("unified_cli")


async def main():
    parser = argparse.ArgumentParser(
        description="Unified Document Ingestion (Vector + Graph)"
    )
    parser.add_argument(
        "--file", type=str, required=True, help="Path to document file (pdf, txt, docx)"
    )
    parser.add_argument("--meta", type=str, help="Optional metadata JSON string")
    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("🚀 Unified Ingestion Pipeline CLI")
    print("=" * 60)
    print(f"File: {file_path.name}")
    print(f"Size: {file_path.stat().st_size / 1024:.2f} KB")
    print("-" * 60)

    loader = UnifiedLoader()

    try:
        # Initialize
        print("🔧 Initializing system components (Async Mode)...")
        await loader.initialize()

        # Execute
        print("⚙️  Submitting job...")
        job_id = await loader.submit_file(str(file_path))
        print(f"✅ Job Submitted: {job_id}")

        print("⏳ Waiting for processing...")

        # Poll for status
        import time

        start_wait = time.time()
        result = None

        while True:
            status_info = await loader.get_job_status(job_id)
            current_state = status_info.get("status", "unknown")

            # Simple progress spinner or indicator
            sys.stdout.write(
                f"\rStatus: {current_state.upper()} ({time.time() - start_wait:.1f}s)"
            )
            sys.stdout.flush()

            if current_state in ["completed", "failed"]:
                print()  # Newline
                result = status_info.get("result")
                break

            await asyncio.sleep(0.5)

        if not result:
            print("❌ Job finished without result object")
            sys.exit(1)

        print("\n" + "=" * 60)
        print("📊 Ingestion Report")
        print("=" * 60)

        # Status Table
        print(f"Document ID:   {result.doc_id}")
        print(f"Overall Status: {'✅ SUCCESS' if result.success else '❌ FAILED'}")
        print("-" * 30)
        print(
            f"1. Vector Store: {status_icon(result.vector_status)} {result.vector_status.upper()}"
        )
        print(
            f"2. Knowledge Graph: {status_icon(result.graph_status)} {result.graph_status.upper()}"
        )
        print(
            f"3. Vector Sync:  {status_icon(result.sync_status)} {result.sync_status.upper()}"
        )
        print("-" * 30)

        if result.node_count > 0:
            print(f"INFO: Created {result.node_count} graph nodes.")

        if result.errors:
            print("\n❌ Errors Encountered:")
            for err in result.errors:
                print(f"  - {err}")

        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Fatal Error: {e}")
        logger.exception("CLI failed")
    finally:
        await loader.close()


def status_icon(status: str) -> str:
    if status in ["indexed", "built", "synced"]:
        return "✅"
    elif status == "failed":
        return "❌"
    elif status == "skipped":
        return "⚠️"
    return "❓"


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
