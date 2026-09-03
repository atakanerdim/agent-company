"""Site data packager: copies company/ content into site/data.
Deterministic; runs in CI and on every Pages deploy. Makes no LLM calls."""
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "site/data"

sys.path.insert(0, str(ROOT / "assets"))
import avatars  # noqa: E402  (the portrait parts library; pure computation, no network)


def roster_public(root):
    """Publish the roster as people.

    Three files describe a colleague and they are deliberately separate: the kernel
    schema in ``roster.json`` (which agent runs on which day), the human identity in
    ``identity.json`` (who they are, in prose a visitor can read), and the wardrobe in
    ``appearance.json`` (what they look like). The site wants all three at once.
    """
    rows = json.loads((root / "company/roster.json").read_text(encoding="utf-8"))
    people = {p["id"]: p for p in json.loads(
        (root / "company/agents/identity.json").read_text(encoding="utf-8"))}
    out = []
    for r in rows:
        who = people.get(r["id"], {})
        out.append({"id": r["id"],
                    "name": who.get("person", r["ad"]),
                    "title": who.get("title", r["ad"]),
                    "room": who.get("room", "The office"),
                    "bio": who.get("bio", ""),
                    "role": r["rol"],
                    "shifts": r["gunler"],
                    "draft": bool(r.get("draft_pr"))})
    return out


# The kernel writes each hallway file as "<colleague>: <what they said>". Models
# keep signing the line as well, so the name arrives twice, and on 2026-09-02 one
# of them opened with the name of a colleague who does not exist:
#
#     Nadia Vance: Liam Zhou: The coffee machine may be gone, but our nightly ...
#
# The page already says who is speaking; it reads that off the roster. So the line
# only has to carry what was said. The prefixes come off here, at the point of
# display — company/hallway keeps exactly what the agent wrote, because that file
# is the evidence and evidence does not get tidied.
#
# Two or three capitalised words before the colon, never one: "Note:" and "Week 35:"
# are things a colleague might legitimately open with, "Liam Zhou:" is not.
SPEAKER = re.compile(r"^\s*[A-Z][\w.'\u2019-]*(?: [A-Z][\w.'\u2019-]*){1,2}\s*:\s*")


def hallway_line(text):
    """Return one hallway line with any speaker prefixes stripped off the front."""
    line = " ".join(text.split("\n")[0].split())
    for _ in range(3):
        shorter = SPEAKER.sub("", line, count=1)
        if shorter == line or not shorter:
            break
        line = shorter
    return line


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
    # The site builds one accuracy table per track and takes their names from here,
    # so a third track appears on the page without the page being touched.
    if (ROOT / "company/data/tracks.json").exists():
        shutil.copy(ROOT / "company/data/tracks.json", OUT / "tracks.json")
    if (ROOT / "company/minutes").exists():
        shutil.copytree(ROOT / "company/minutes", OUT / "minutes")
    if (ROOT / "company/hallway").exists():
        (OUT / "hallway").mkdir(parents=True, exist_ok=True)
        for src in sorted((ROOT / "company/hallway").glob("*.txt")):
            (OUT / "hallway" / src.name).write_text(
                hallway_line(src.read_text(encoding="utf-8")) + "\n", encoding="utf-8")
    shutil.copytree(ROOT / "company/agents/prompts", OUT / "prompts")
    shutil.copy(ROOT / "company/constitution.md", OUT / "constitution.md")
    avatars.write_all(OUT / "avatars", ROOT)

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
