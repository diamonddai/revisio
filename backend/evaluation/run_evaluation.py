"""CLI entry point for the evaluation pipeline.

Usage:
    cd backend
    conda activate frame
    python -m evaluation.run_evaluation --cases C01,C02 --runs 3 --output eval_output/
    python -m evaluation.run_evaluation --report-only --output eval_output/   # regenerate report from cache
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evaluation.runner import SimRunResult


def _save_cache(run_results: dict[str, list[SimRunResult]], path: Path) -> None:
    """Persist run results to JSON so reports can be regenerated without re-running."""
    serializable: dict[str, list[dict]] = {}
    for cid, results in run_results.items():
        serializable[cid] = [
            {
                "case_id": r.case_id,
                "condition": r.condition,
                "all_operations": r.all_operations,
                "ops_by_depth": {str(k): v for k, v in r.ops_by_depth.items()},
                "cum_ops_trajectory": r.cum_ops_trajectory,
                "node_count": r.node_count,
                "edge_count": r.edge_count,
            }
            for r in results
        ]
    path.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_cache(path: Path) -> dict[str, list[SimRunResult]]:
    """Load cached run results from JSON."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    results: dict[str, list[SimRunResult]] = {}
    for cid, items in raw.items():
        results[cid] = [
            SimRunResult(
                case_id=item["case_id"],
                condition=item["condition"],
                all_operations=item["all_operations"],
                ops_by_depth={int(k): v for k, v in item["ops_by_depth"].items()},
                cum_ops_trajectory=item["cum_ops_trajectory"],
                node_count=item["node_count"],
                edge_count=item["edge_count"],
            )
            for item in items
        ]
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Run framing simulation evaluation")
    parser.add_argument(
        "--cases",
        type=str,
        default=None,
        help="Comma-separated case IDs (default: all mappable cases)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="Number of repeated runs per condition (default: 3)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="eval_output",
        help="Output directory for report and plots (default: eval_output/)",
    )
    parser.add_argument(
        "--skip-random",
        action="store_true",
        help="Skip random baseline runs (for quick testing)",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Regenerate report from cached results (no simulation)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress verbose output",
    )
    args = parser.parse_args()

    from evaluation.ground_truth import load_all_lineages
    from evaluation.report import compute_all_metrics, generate_markdown_report, plot_drift_trajectories

    print("Loading ground truth lineages...")
    lineages = load_all_lineages()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_path = output_dir / "run_results_cache.json"

    if args.report_only:
        if not cache_path.exists():
            print(f"ERROR: No cached results at {cache_path}. Run evaluation first.")
            return
        print(f"Loading cached results from {cache_path}...")
        run_results = _load_cache(cache_path)
        print(f"  Loaded {sum(len(v) for v in run_results.values())} runs across {len(run_results)} cases")
    else:
        from evaluation.runner import load_case_mapping, run_evaluation
        case_mapping = load_case_mapping()
        print(f"  Loaded {len(lineages)} lineages, {len(case_mapping)} mappable cases")

        case_ids = None
        if args.cases:
            case_ids = [c.strip() for c in args.cases.split(",")]
            print(f"  Target cases: {case_ids}")

        print(f"\nRunning evaluation (runs={args.runs}, skip_random={args.skip_random})...")
        run_results = run_evaluation(
            lineages=lineages,
            case_mapping=case_mapping,
            case_ids=case_ids,
            n_runs=args.runs,
            skip_random=args.skip_random,
            verbose=not args.quiet,
        )

        print(f"\nSaving results cache to {cache_path}...")
        _save_cache(run_results, cache_path)

    print("\nComputing metrics...")
    case_metrics = compute_all_metrics(lineages, run_results)

    print("Generating report...")
    report_md = generate_markdown_report(case_metrics, n_runs=args.runs)
    report_path = output_dir / "evaluation_report.md"
    report_path.write_text(report_md, encoding="utf-8")
    print(f"  Report written to {report_path}")

    print("Generating plots...")
    plots_dir = output_dir / "plots"
    plot_paths = plot_drift_trajectories(
        case_metrics=case_metrics,
        lineages=lineages,
        run_results=run_results,
        output_dir=plots_dir,
    )
    for p in plot_paths:
        print(f"  Plot: {p}")

    print(f"\n{'='*60}")
    print("Evaluation complete!")
    print(f"  Output directory: {output_dir}")
    print(f"\n{report_md}")


if __name__ == "__main__":
    main()
