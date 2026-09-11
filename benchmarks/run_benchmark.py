"""benchmarks/run_benchmark.py -- Single-command benchmark runner.

Produces benchmarks/report.json with:
  - job_success_rate: fraction of benchmark jobs that complete without error
  - time_per_job_seconds: wall-clock time for the CPU-side pipeline (job build + validate)
  - local_ram_mb: peak RAM used during the CPU pipeline (measured via tracemalloc)
  - safety_check_ms: time for full_check() on a typical prompt
  - spec_validation_ms: time for AvatarSpec validation
  - test_suite_result: pass/fail summary from pytest

Usage:
  python benchmarks/run_benchmark.py

Output:
  benchmarks/report.json  (machine-readable)
  Prints human-readable summary to stdout
"""

from __future__ import annotations

import json
import sys
import time
import tracemalloc
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def _build_benchmark_spec():
    """Build a standard spec for benchmarking."""
    from avatarpipe.spec import AgeBand, AvatarSpec, HairSpec
    return AvatarSpec(
        age_band=AgeBand.adult,
        skin_tone="Fitzpatrick III",
        hair=HairSpec(style="short curly", color="dark brown"),
        attire="business casual blazer",
        background="modern office, soft bokeh",
        seed=42,
    )


def _benchmark_spec_validation(n: int = 100) -> float:
    """Time n AvatarSpec validations. Returns ms per validation."""
    from avatarpipe.spec import AgeBand, AvatarSpec, HairSpec
    kwargs = {
        "age_band": AgeBand.adult,
        "skin_tone": "Fitzpatrick III",
        "hair": HairSpec(style="short curly", color="dark brown"),
        "attire": "business casual",
        "background": "studio",
        "seed": 42,
    }
    start = time.perf_counter()
    for _ in range(n):
        AvatarSpec(**kwargs)
    elapsed = time.perf_counter() - start
    return (elapsed / n) * 1000  # ms


def _benchmark_safety_check(n: int = 100) -> float:
    """Time n full_check() calls. Returns ms per call."""
    from avatarpipe.safety import full_check
    prompt = "a professional adult person, business casual blazer, modern office, photorealistic"
    spec = {"attire": "business casual blazer", "background": "modern office", "skin_tone": "Fitzpatrick III", "pose": "neutral"}
    start = time.perf_counter()
    for _ in range(n):
        full_check(prompt, spec)
    elapsed = time.perf_counter() - start
    return (elapsed / n) * 1000  # ms


def _benchmark_cpu_pipeline(config_dir: Path, n: int = 5) -> dict:
    """Benchmark the full CPU-side pipeline (build + stub run + validate + manifest).
    Returns timing and RAM metrics."""
    import yaml
    import tempfile
    from avatarpipe.job_builder import build_job, save_job
    from avatarpipe.inference_adapter import LocalCPUStubAdapter
    from avatarpipe.output_validator import validate_outputs
    from avatarpipe.manifest import write_manifest

    spec = _build_benchmark_spec()
    times = []
    success = 0

    tracemalloc.start()
    peak_mem_before = tracemalloc.get_traced_memory()[1]

    for _ in range(n):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            t0 = time.perf_counter()
            try:
                job = build_job(spec, config_dir)
                save_job(job, tmp / "jobs")
                adapter = LocalCPUStubAdapter()
                fragment = adapter.run(job, tmp / "results")
                images = [Path(p) for p in fragment["images"]]
                report = validate_outputs(job, images, tmp / "results")
                write_manifest(job, images, tmp / "results")
                success += 1
            except Exception:
                pass
            times.append(time.perf_counter() - t0)

    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return {
        "runs": n,
        "success_count": success,
        "job_success_rate": success / n,
        "mean_time_seconds": round(sum(times) / len(times), 4),
        "min_time_seconds": round(min(times), 4),
        "max_time_seconds": round(max(times), 4),
        "peak_ram_mb": round((peak_mem - peak_mem_before) / 1024 / 1024, 2),
    }


def _run_pytest() -> dict:
    """Run pytest and return a summary dict."""
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=no"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )
    last_line = result.stdout.strip().split("\n")[-1] if result.stdout.strip() else "no output"
    return {
        "returncode": result.returncode,
        "passed": result.returncode == 0,
        "summary": last_line,
    }


def main():
    project_root = Path(__file__).parent.parent
    config_dir = project_root / "config"
    output_dir = project_root / "benchmarks"
    output_dir.mkdir(exist_ok=True)

    print("Running avatarpipe benchmarks...")

    report = {
        "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "python_version": sys.version,
    }

    print("  [1/4] Spec validation speed...")
    report["spec_validation_ms"] = round(_benchmark_spec_validation(), 3)

    print("  [2/4] Safety check speed...")
    report["safety_check_ms"] = round(_benchmark_safety_check(), 3)

    print("  [3/4] CPU pipeline benchmark (5 runs)...")
    pipeline_results = _benchmark_cpu_pipeline(config_dir, n=5)
    report.update(pipeline_results)

    print("  [4/4] Running pytest suite...")
    report["test_suite"] = _run_pytest()

    # Write report
    report_path = output_dir / "report.json"
    with report_path.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    # Human-readable summary
    print("\n" + "="*50)
    print("BENCHMARK RESULTS")
    print("="*50)
    print(f"  Spec validation:   {report['spec_validation_ms']:.3f} ms/call")
    print(f"  Safety check:      {report['safety_check_ms']:.3f} ms/call")
    print(f"  Job success rate:  {report['job_success_rate']*100:.0f}%")
    print(f"  Mean pipeline time:{report['mean_time_seconds']:.3f} s")
    print(f"  Peak local RAM:    {report['peak_ram_mb']:.1f} MB")
    print(f"  Test suite:        {'PASS' if report['test_suite']['passed'] else 'FAIL'} ({report['test_suite']['summary']})")
    print(f"\n  Report written to: {report_path}")

    return 0 if report["test_suite"]["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
