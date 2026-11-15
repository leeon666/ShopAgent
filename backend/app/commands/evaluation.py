"""CLI for reproducible ShopAgent evaluation."""

import json

import click

from app.commands import command, info, success
from app.evaluation.after_sales import run_evaluation


@command("eval-after-sales", help="Run the three-way after-sales evaluation")
@click.option(
    "--mode",
    "modes",
    multiple=True,
    type=click.Choice(["llm_only", "llm_rag", "full_agent"]),
    default=("full_agent",),
    show_default=True,
)
@click.option("--limit", type=click.IntRange(min=1), default=None, help="Run only the first N cases")
@click.option("--concurrency", type=click.IntRange(min=1, max=8), default=3, show_default=True)
def eval_after_sales(modes: tuple[str, ...], limit: int | None, concurrency: int) -> None:
    """Run all selected baselines and print aggregate metrics."""
    info(
        f"Running evaluation modes={list(modes)} limit={limit or 'all'} "
        f"concurrency={concurrency}"
    )

    def show_progress(done: int, total: int, mode: str, case_id: str) -> None:
        info(f"[{done:>2}/{total}] {mode} {case_id}")

    report = run_evaluation(
        modes=list(modes),
        limit=limit,
        concurrency=concurrency,
        progress=show_progress,
    )
    click.echo(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    success(f"Full result written to {report['output_path']}")
