"""
Stage 5: PIPELINE ORCHESTRATOR
ingest -> validate -> transform -> metrics, with logging, rerun-safety, and failure handling.
Each stage's failure stops the run with a clear message rather than continuing on bad data.
"""
import argparse
import logging
import sys
import traceback

import config
import ingest
import validate
import transform
import metrics


def run(month: str, force: bool = False):
    log_file = config.LOG_DIR / f"pipeline_{month}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
    )
    log = logging.getLogger("pipeline")
    log.info(f"=== PIPELINE START: month={month} force={force} ===")

    stages = [
        ("ingest", lambda: ingest.run(month, force)),
        ("validate", lambda: validate.validate(month)),
        ("transform", lambda: transform.transform(month)),
        ("metrics", lambda: metrics.compute_metrics(month)),
    ]

    for name, fn in stages:
        log.info(f"--- stage: {name} ---")
        try:
            fn()
        except Exception as e:
            log.error(f"STAGE FAILED: {name} — {e}")
            log.debug(traceback.format_exc())
            log.error(f"=== PIPELINE HALTED at '{name}'. Fix the issue above and re-run; "
                      f"earlier stages' outputs are preserved and will be skipped unless --force. ===")
            sys.exit(1)

    log.info(f"=== PIPELINE COMPLETE: see data/output/metrics_{month}.md ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NYC TLC trip reliability pipeline")
    parser.add_argument("--month", default="2025-01", help="YYYY-MM, e.g. 2025-01")
    parser.add_argument("--force", action="store_true", help="re-download/re-run even if outputs exist")
    args = parser.parse_args()
    run(args.month, args.force)