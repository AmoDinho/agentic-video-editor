from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from ave.config import load_config
from ave.edl.schema import EDL
from ave.edl.validator import index_from_paths, validate_edl
from ave.hardware import detect
from ave.render.engine import render_edl

app = typer.Typer(no_args_is_help=True, add_completion=False, help="Local agentic video editor")


@app.command()
def doctor() -> None:
    info = detect()
    typer.echo(json.dumps(info, indent=2))
    raise typer.Exit(0 if info["ok"] else 1)


@app.command("generate-samples")
def generate_samples_cmd(
    dest: Path = typer.Argument(Path("samples"), help="Directory for sample media"),
) -> None:
    from ave.samples import generate_samples

    paths = generate_samples(dest)
    for k, v in paths.items():
        typer.echo(f"{k}: {v}")


@app.command()
def render(
    edl_path: Path = typer.Argument(..., exists=True),
    output: Path = typer.Option(Path("out.mp4"), "--output", "-o"),
    mode: str = typer.Option("final", "--mode", help="preview or final"),
) -> None:
    edl = EDL.load(edl_path)
    base = edl_path.parent
    resolved = edl.resolved(base)
    paths = [Path(s.source) for s in resolved.segments]
    idx = index_from_paths(list(dict.fromkeys(paths)))
    result = validate_edl(edl, idx, base=base, check_words=False, check_order=False, check_target=False)
    if not result.ok:
        typer.echo(result.model_dump_json(indent=2))
        raise typer.Exit(1)
    out = render_edl(edl, output, mode=mode, base=base)  # type: ignore[arg-type]
    typer.echo(str(out))


@app.command()
def analyze(
    folder: Path = typer.Argument(..., exists=True, file_okay=True),
    force: bool = typer.Option(False, "--force"),
) -> None:
    from ave.analysis.pipeline import analyze_file, analyze_folder

    cfg = load_config()

    def emit(ev):
        typer.echo(json.dumps(ev))

    if folder.is_file():
        data = analyze_file(folder, config=cfg, emit=emit, force=force)
        typer.echo(data.get("path"))
        return
    results = analyze_folder(folder, config=cfg, emit=emit)
    typer.echo(json.dumps({"count": len(results), "files": [r.get("path") for r in results]}))


@app.command("profile")
def profile_cmd(
    reference: Path = typer.Argument(..., exists=True),
    output: Optional[Path] = typer.Option(None, "--output", "-o"),
) -> None:
    from ave.style.profile import build_style_profile, save_profile

    profile = build_style_profile(reference)
    dest = output or Path("style_profile.json")
    save_profile(profile, dest)
    typer.echo(json.dumps({k: profile[k] for k in profile if k != "summary"}, indent=2))
    typer.echo(profile["summary"])


@app.command()
def assemble(
    clips: Path = typer.Argument(..., exists=True),
    reference: Path = typer.Option(..., "--reference", "-r", exists=True),
    target: float = typer.Option(..., "--target", "-t"),
    output: Path = typer.Option(Path("edl.json"), "--output", "-o"),
    project_id: str = typer.Option("cli", "--project-id"),
) -> None:
    from ave.analysis.pipeline import analyze_file, analyze_folder
    from ave.heuristic.assembler import assemble as heuristic_assemble
    from ave.style.profile import build_style_profile

    cfg = load_config()
    analyses = analyze_folder(clips, config=cfg) if clips.is_dir() else [analyze_file(clips, config=cfg)]
    style = build_style_profile(reference, config=cfg)
    edl = heuristic_assemble(
        analyses, style, project_id=project_id, target_duration_s=target
    )
    edl.save(output)
    typer.echo(str(output))
    typer.echo(edl.notes)


@app.command()
def edit(
    clips: Path = typer.Argument(..., exists=True),
    reference: Path = typer.Option(..., "--reference", "-r", exists=True),
    target: float = typer.Option(..., "--target", "-t"),
    brief: str = typer.Option("", "--brief"),
    output: Path = typer.Option(Path("edl.json"), "--output", "-o"),
    project_id: str = typer.Option("cli", "--project-id"),
    mode: str = typer.Option("agent", "--mode", help="agent or heuristic"),
) -> None:
    from ave.agent.loop import run_agent
    from ave.analysis.pipeline import analyze_file, analyze_folder
    from ave.heuristic.assembler import assemble as heuristic_assemble
    from ave.style.profile import build_style_profile

    cfg = load_config()
    analyses = analyze_folder(clips, config=cfg) if clips.is_dir() else [analyze_file(clips, config=cfg)]
    style = build_style_profile(reference, config=cfg)
    if mode == "heuristic":
        edl = heuristic_assemble(analyses, style, project_id=project_id, target_duration_s=target)
    else:
        edl = run_agent(
            analyses,
            style,
            project_id=project_id,
            target_duration_s=target,
            brief=brief,
            config=cfg,
            emit=lambda ev: typer.echo(json.dumps(ev, default=str)[:500]),
        )
    edl.save(output)
    typer.echo(str(output))


@app.command()
def export(
    edl_path: Path = typer.Argument(..., exists=True),
    dest: Path = typer.Option(Path("export"), "--dest", "-d"),
    media: bool = typer.Option(True, "--media/--no-media"),
) -> None:
    from ave.export.otio import export_timeline

    edl = EDL.load(edl_path)
    paths = export_timeline(edl, dest, base=edl_path.parent)
    if media:
        out = dest / f"{edl.project_id}.mp4"
        render_edl(edl, out, mode="final", base=edl_path.parent)
        paths["mp4"] = str(out)
    typer.echo(json.dumps(paths, indent=2))


@app.command()
def eval(
    edl_path: Path = typer.Argument(..., exists=True),
    clips: Path = typer.Option(..., "--clips", exists=True),
    reference: Path = typer.Option(..., "--reference", exists=True),
) -> None:
    from ave.analysis.pipeline import analyze_folder
    from ave.eval.metrics import score_run
    from ave.style.profile import build_style_profile

    cfg = load_config()
    edl = EDL.load(edl_path)
    analyses = analyze_folder(clips, config=cfg)
    style = build_style_profile(reference, config=cfg)
    typer.echo(json.dumps(score_run(edl, analyses, style), indent=2))


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8000, "--port"),
) -> None:
    import uvicorn

    uvicorn.run("ave.api.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    app()
