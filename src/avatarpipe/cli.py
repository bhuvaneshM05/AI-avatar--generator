"""avatarpipe CLI -- Typer-based command-line interface.

Entry point: `avatarpipe` (registered in pyproject.toml [project.scripts])

All subcommands follow this pattern:
  1. Parse and validate inputs (Typer + Pydantic)
  2. Perform the operation
  3. Print structured output via Rich
  4. Exit with 0 on success, non-zero on any error -- never a raw traceback

Design: commands import lazily (inside the function body) to keep CLI startup
fast even when heavyweight libraries (torch, diffusers) are installed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# ---------------------------------------------------------------------------
# App and console setup
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="avatarpipe",
    help="AI human-avatar generation pipeline (PS02).",
    add_completion=False,
    pretty_exceptions_show_locals=False,  # never leak internals in production
)

# Two consoles: stdout for normal output, stderr for errors/warnings.
console = Console()
err_console = Console(stderr=True, style="bold red")


def _exit_error(message: str, code: int = 1) -> None:
    """Print an error panel to stderr and exit with the given code."""
    err_console.print(Panel(f"[red]{message}[/red]", title="Error", border_style="red"))
    raise typer.Exit(code=code)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_spec_yaml(spec_path: Path):
    """Load and validate an AvatarSpec from a YAML file."""
    import yaml
    from pydantic import ValidationError
    from avatarpipe.spec import AvatarSpec

    if not spec_path.exists():
        _exit_error(f"Spec file not found: {spec_path}")

    with spec_path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    try:
        return AvatarSpec(**raw)
    except ValidationError as exc:
        _exit_error(f"Spec validation failed:\n{exc}")


def _default_config_dir() -> Path:
    """Return the config/ directory relative to the project root."""
    pkg_dir = Path(__file__).parent.parent.parent  # src/avatarpipe -> project root
    candidate = pkg_dir / "config"
    if candidate.exists():
        return candidate
    return Path.cwd() / "config"


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

@app.command("new-job")
def new_job(
    spec: Path = typer.Option(..., "--spec", help="Path to the avatar spec YAML file"),
    jobs_dir: Path = typer.Option(Path("jobs"), "--jobs-dir", help="Directory for job bundles"),
    config_dir: Optional[Path] = typer.Option(None, "--config-dir", help="Path to config/ directory"),
    skip_safety: bool = typer.Option(False, "--skip-safety", help="Skip safety pre-check (testing only)"),
) -> None:
    """Validate a spec YAML, run safety pre-check, and create a job bundle."""
    from avatarpipe.job_builder import build_job, save_job

    resolved_config = config_dir or _default_config_dir()

    # 1. Load + validate spec
    avatar_spec = _load_spec_yaml(spec)
    console.print(f"[green]checkmark[/green] Spec validated: [bold]{spec}[/bold]")

    # 2. Safety pre-check
    if not skip_safety:
        from avatarpipe.safety import full_check
        prompt, _ = avatar_spec.to_prompt()
        result = full_check(prompt, avatar_spec.to_dict())
        if not result.passed:
            _exit_error(f"Safety pre-check BLOCKED this job:\n{result.reason}", code=2)
        if result.severity.value == "flag":
            console.print(f"[yellow]WARNING Safety flag:[/yellow] {result.reason}")

    # 3. Build job bundle
    try:
        job = build_job(avatar_spec, resolved_config)
    except Exception as exc:
        _exit_error(f"Failed to build job: {exc}")

    # 4. Save job bundle
    try:
        job_path = save_job(job, jobs_dir)
    except Exception as exc:
        _exit_error(f"Failed to save job: {exc}")

    # 5. Print success summary
    console.print(Panel(
        f"[bold green]Job created successfully[/bold green]\n"
        f"Job ID  : [cyan]{job['job_id']}[/cyan]\n"
        f"Path    : [cyan]{job_path}[/cyan]\n"
        f"Model   : [cyan]{job['model'].get('name', 'unknown')}[/cyan]\n"
        f"Seed    : [cyan]{job['seed']}[/cyan]\n"
        f"Route   : [cyan]{job['provenance_route']}[/cyan]",
        title="new-job",
        border_style="green",
    ))


@app.command("prepare-notebook")
def prepare_notebook(
    job: Path = typer.Option(..., "--job", help="Path to the job bundle JSON"),
    notebook: Path = typer.Option(
        Path("notebooks/inference_kaggle.ipynb"),
        "--notebook",
        help="Path to the Kaggle inference notebook",
    ),
    staging_dir: Path = typer.Option(Path("jobs/staging"), "--staging-dir"),
) -> None:
    """Stage a job bundle and print Kaggle upload instructions."""
    import shutil
    from avatarpipe.job_builder import load_job

    try:
        bundle = load_job(job)
    except Exception as exc:
        _exit_error(f"Failed to load job: {exc}")

    staging_dir.mkdir(parents=True, exist_ok=True)
    staged = staging_dir / job.name
    shutil.copy2(job, staged)

    console.print(Panel(
        f"[bold]Job bundle staged:[/bold] [cyan]{staged}[/cyan]\n\n"
        "[bold]Kaggle steps:[/bold]\n"
        "1. Go to kaggle.com -> Datasets -> New Dataset\n"
        f"2. Upload: [cyan]{staged}[/cyan]\n"
        "3. Open [bold]notebooks/inference_kaggle.ipynb[/bold] in Kaggle\n"
        "4. Attach dataset; set KAGGLE_JOB_PATH to the uploaded file path\n"
        "5. Run All -> download output images + result_fragment.json\n"
        f"6. Run: [bold]avatarpipe ingest --job {job} --result-dir <downloaded/>[/bold]",
        title="prepare-notebook",
        border_style="blue",
    ))


@app.command("run-local")
def run_local(
    job: Path = typer.Option(..., "--job", help="Path to the job bundle JSON"),
    output_dir: Path = typer.Option(Path("local_output"), "--output-dir", help="Directory to store outputs"),
    auto_ingest: bool = typer.Option(True, "--auto-ingest/--no-auto-ingest", help="Automatically validate and write manifest"),
) -> None:
    """Run local CPU stub inference (instant plumbing test without GPU)."""
    from avatarpipe.job_builder import load_job
    from avatarpipe.inference_adapter import LocalCPUStubAdapter

    try:
        bundle = load_job(job)
    except Exception as exc:
        _exit_error(f"Failed to load job: {exc}")

    output_dir.mkdir(parents=True, exist_ok=True)
    adapter = LocalCPUStubAdapter(width=512, height=512)

    with console.status("[bold green]Executing local CPU stub inference..."):
        fragment = adapter.run(bundle, output_dir)

    console.print(f"[green]OK[/green] Generated local stub artifact: [cyan]{fragment['images'][0]}[/cyan]")
    console.print(f"[yellow]Notice:[/yellow] Provenance route is [bold]{fragment['provenance_route']}[/bold] (CPU test mode).")

    if auto_ingest:
        image_files = [Path(p) for p in fragment["images"]]
        from avatarpipe.output_validator import validate_outputs
        from avatarpipe.manifest import write_manifest
        report = validate_outputs(bundle, image_files, output_dir)
        manifest_path = write_manifest(bundle, image_files, output_dir, validation_report=report, result_fragment=fragment)
        console.print(f"[green]OK[/green] Manifest written: [cyan]{manifest_path}[/cyan]")


@app.command("ingest")
def ingest(
    job: Path = typer.Option(..., "--job", help="Path to the original job bundle JSON"),
    result_dir: Path = typer.Option(..., "--result-dir", help="Directory with inference outputs"),
) -> None:
    """Validate inference outputs and write avatar_manifest.json."""
    from avatarpipe.job_builder import load_job

    try:
        bundle = load_job(job)
    except Exception as exc:
        _exit_error(f"Failed to load job: {exc}")

    if not result_dir.exists():
        _exit_error(f"Result directory not found: {result_dir}")

    image_files = list(result_dir.glob("*.png")) + list(result_dir.glob("*.jpg"))
    if not image_files:
        _exit_error(f"No image files (*.png, *.jpg) found in {result_dir}")

    # Output validation
    try:
        from avatarpipe.output_validator import validate_outputs
        report = validate_outputs(bundle, image_files, result_dir)
        console.print(f"[green]OK[/green] Validated {len(image_files)} image(s)")
    except ImportError:
        console.print("[yellow]WARNING output_validator.py not yet available[/yellow]")
        report = {"validated": False}

    # Write manifest
    try:
        from avatarpipe.manifest import write_manifest
        manifest_path = write_manifest(bundle, image_files, result_dir, validation_report=report)
        console.print(f"[green]OK[/green] Manifest written: [cyan]{manifest_path}[/cyan]")
    except ImportError:
        manifest_path = result_dir / "avatar_manifest.json"
        minimal = {"job_id": bundle["job_id"], "images": [str(p) for p in image_files], "validation": report}
        manifest_path.write_text(json.dumps(minimal, indent=2))
        console.print(f"[yellow]WARNING[/yellow] Minimal manifest written: [cyan]{manifest_path}[/cyan]")

    console.print(Panel(
        f"Job ID  : [cyan]{bundle['job_id']}[/cyan]\n"
        f"Images  : [cyan]{len(image_files)}[/cyan]\n"
        f"Manifest: [cyan]{manifest_path}[/cyan]",
        title="ingest complete",
        border_style="green",
    ))


@app.command("evaluate")
def evaluate(
    run: str = typer.Option(..., "--run", help="Run ID or path to avatar_manifest.json"),
) -> None:
    """Load a manifest and run adherence + diversity scoring."""
    manifest_path = Path(run)
    if manifest_path.is_dir():
        manifest_path = manifest_path / "avatar_manifest.json"
    if not manifest_path.exists():
        _exit_error(f"Manifest not found: {manifest_path}")

    with manifest_path.open("r", encoding="utf-8") as fh:
        manifest = json.load(fh)

    console.print(f"[green]OK[/green] Loaded manifest for job [cyan]{manifest.get('job_id', 'unknown')}[/cyan]")

    try:
        from avatarpipe.evaluation import run_evaluation  # type: ignore
        scores = run_evaluation(manifest)
        table = Table(title="Evaluation Scores")
        table.add_column("Metric", style="cyan")
        table.add_column("Score", justify="right")
        for k, v in scores.items():
            table.add_row(str(k), f"{v:.4f}" if isinstance(v, float) else str(v))
        console.print(table)
    except (ImportError, AttributeError):
        console.print("[yellow]WARNING evaluation metrics not yet implemented[/yellow]")


@app.command("validate-consent")
def validate_consent(
    consent_id: str = typer.Option(..., "--consent-id", help="Consent record ID to validate"),
) -> None:
    """Check that a consent record exists and is valid (Exceptional tier)."""
    try:
        from avatarpipe.consent import check_consent  # type: ignore
        result = check_consent(consent_id)
        if result.valid:
            console.print(f"[green]OK[/green] Consent [cyan]{consent_id}[/cyan] is valid")
        else:
            _exit_error(f"Consent {consent_id} is invalid: {result.reason}", code=3)
    except ImportError:
        console.print(f"[yellow]WARNING consent.py not yet implemented.[/yellow] ID: [cyan]{consent_id}[/cyan]")


@app.command("list-jobs")
def list_jobs(
    jobs_dir: Path = typer.Option(Path("jobs"), "--jobs-dir"),
) -> None:
    """List all job bundles with their status."""
    if not jobs_dir.exists():
        console.print(f"[yellow]Jobs directory not found: {jobs_dir}[/yellow]")
        raise typer.Exit(0)

    job_files = sorted([f for f in jobs_dir.glob("*.json") if f.is_file()])
    if not job_files:
        console.print("[yellow]No job bundles found.[/yellow]")
        raise typer.Exit(0)

    table = Table(title=f"Jobs in {jobs_dir}", show_lines=True)
    table.add_column("Job ID", style="cyan", no_wrap=True)
    table.add_column("Created At")
    table.add_column("Model", style="green")
    table.add_column("Seed", justify="right", style="magenta")
    table.add_column("Route", style="yellow")

    for jf in job_files:
        try:
            with jf.open("r", encoding="utf-8") as fh:
                b = json.load(fh)
            table.add_row(
                b.get("job_id", jf.stem)[:36],
                b.get("created_at", "?"),
                b.get("model", {}).get("name", "?"),
                str(b.get("seed", "?")),
                b.get("provenance_route", "?"),
            )
        except Exception as exc:
            table.add_row(jf.stem, "PARSE ERROR", str(exc), "", "")

    console.print(table)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app()
