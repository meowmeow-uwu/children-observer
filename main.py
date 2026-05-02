"""
AI Child Guardian - Main Entry Point.

Usage:
    # Chạy edge pipeline (giám sát camera)
    python main.py --mode edge

    # Chạy compliance check
    python main.py --mode compliance

    # Chuẩn bị dataset
    python main.py --mode prepare-data
"""

import argparse
import sys

from loguru import logger


def run_edge_pipeline():
    """Khởi chạy edge processing pipeline."""
    from module_edge_firmware.pipeline import EdgePipeline

    pipeline = EdgePipeline()
    pipeline.start()


def run_compliance_check():
    """Chạy compliance checks."""
    from module_security.compliance_checker import ComplianceChecker

    checker = ComplianceChecker()
    results = checker.run_all_checks()

    for result in results:
        status = "✅ PASSED" if result.passed else "❌ FAILED"
        print(f"\n{result.standard}: {status} ({result.pass_rate:.0%})")
        for check in result.checks:
            icon = "✅" if check["passed"] else "❌"
            print(f"  {icon} {check['id']}: {check['name']}")
        for warning in result.warnings:
            print(f"  ⚠️  {warning}")


def prepare_data():
    """Chuẩn bị cấu trúc dataset."""
    from pathlib import Path

    datasets = {
        "childsun": Path("./data/childsun"),
        "violence": Path("./data/violence"),
    }

    for name, path in datasets.items():
        for split in ["train", "val", "test"]:
            (path / split / "images").mkdir(parents=True, exist_ok=True)
            (path / split / "labels").mkdir(parents=True, exist_ok=True)
        logger.info(f"Created dataset structure: {path}")

    logger.info("Dataset directories ready. Place your data files accordingly.")


def main():
    parser = argparse.ArgumentParser(
        description="AI Child Guardian - Hệ thống Giám sát & Bảo vệ Trẻ em"
    )
    parser.add_argument(
        "--mode",
        choices=["edge", "compliance", "prepare-data"],
        default="edge",
        help="Chế độ chạy (default: edge)",
    )
    args = parser.parse_args()

    from configs.logging_config import setup_logging
    setup_logging()

    logger.info(f"AI Child Guardian starting | mode={args.mode}")

    if args.mode == "edge":
        run_edge_pipeline()
    elif args.mode == "compliance":
        run_compliance_check()
    elif args.mode == "prepare-data":
        prepare_data()


if __name__ == "__main__":
    main()
