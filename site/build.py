"""Site data packager: copies company/ content into site/data.
Deterministic; runs in CI and on every Pages deploy. Makes no LLM calls."""
import datetime as dt
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "site/data"


def roster_public(root):
    """Publish the roster with public field names; the internal file keeps the kernel schema."""
    rows = json.loads((root / "company/roster.json").read_text(encoding="utf-8"))
    return [{"id": r["id"], "name": r["ad"], "role": r["rol"],
             "shifts": r["gunler"], "draft": bool(r.get("draft_pr"))} for r in rows]


def changelog(root, agent_ids):
    """Only autonomous merges belong on the public changelog.

    An agent commit is titled '<agent id>: ...' (or 'predictions: ...' for the personas).
    Anything else — repository scaffolding, tooling, operator commits — is left out.
    """
    prefixes = tuple(f"{a}: " for a in agent_ids) + ("predictions: ",)
    entries = []
    try:
        out = subprocess.run(["git", "log", "-n", "300", "--pretty=format:%as%x09%s"],
                             cwd=root, capture_output=True, text=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return entries
    for line in out.splitlines():
        date, _, subject = line.partition("\t")
        if subject.startswith(prefixes):
            entries.append({"date": date, "message": subject})
    return entries


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    for name in ("fixtures", "predictions", "results", "scores"):
        source = ROOT / "company/data" / name
        if source.exists():
            shutil.copytree(source, OUT / name)
    if (ROOT / "company/data/league.json").exists():
        shutil.copy(ROOT / "company/data/league.json", OUT / "league.json")
    for folder in ("minutes", "hallway"):
        if (ROOT / "company" / folder).exists():
            shutil.copytree(ROOT / "company" / folder, OUT / folder)
    shutil.copytree(ROOT / "company/agents/prompts", OUT / "prompts")
    shutil.copy(ROOT / "company/constitution.md", OUT / "constitution.md")

    roster = roster_public(ROOT)
    (OUT / "roster.json").write_text(
        json.dumps(roster, ensure_ascii=False, indent=1), encoding="utf-8")

    # Company name: read from the "Company name:" line of the constitution.
    name = ""
    for line in (ROOT / "company/constitution.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("Company name:") and "not chosen" not in line:
            name = line.split(":", 1)[1].strip()
    (OUT / "name.txt").write_text(name, encoding="utf-8")

    (OUT / "changelog.json").write_text(
        json.dumps(changelog(ROOT, [r["id"] for r in roster]), ensure_ascii=False),
        encoding="utf-8")

    files = sorted(p.relative_to(OUT).as_posix() for p in OUT.rglob("*") if p.is_file())
    (OUT / "manifest.json").write_text(json.dumps(
        {"generated": dt.datetime.utcnow().isoformat(timespec="seconds"), "files": files},
        ensure_ascii=False), encoding="utf-8")
    print(f"site/data ready: {len(files)} files")


if __name__ == "__main__":
    main()
