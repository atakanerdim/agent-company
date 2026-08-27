"""A file an agent writes has to parse. Nothing else about it can be checked cheaply.

The site has gone dark twice, both times through the editor, and the second time
walked straight through the fence built after the first.

  2026-08-19  site/app.js came back cut off mid-word and site/style.css came back
              as the sentence "/* No changes needed */". Both were much smaller
              than what they replaced, so SHRINK_FLOOR now catches that shape.

  2026-08-26  site/app.js came back 252 bytes LARGER, complete top to bottom, and
              did not run: a quote had become an escape on line 8 and three join()
              calls had grown a third quote. SHRINK_FLOOR cannot see this, because
              nothing shrank. CI was green — no test looked at the file — and every
              page on the site rendered as an empty shell for five days.

  2026-08-25  the same week, on an open branch, site/style.css lost the ":root"
              in front of its opening brace. Braces still balanced. Every colour,
              font and spacing rule in the stylesheet would have stopped applying.

Size was never the thing that mattered. These tests hold the fence that measures
the thing that does.
"""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

AGENT = {"id": "webdev", "ad": "Kiran Menon", "rol": "site", "logic": "editor",
         "alan": ["site/"], "gunler": ["wed", "sat"], "draft_pr": False}

# The line that took the site down on 2026-08-26, copied out of the merged commit.
BROKEN_JS_LINE = (
    'const esc=s=>String(s).replace(/[&<>"\']/g,'
    'c=>({"&":"&amp;","<":"&lt;","\\":"&gt;","\'":"&quot;"}[c]));'
)


def _module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _validate(root=ROOT):
    return _module("logic_validate_under_test",
                   root / "company/agents/logic/validate.py")


def _editor(company):
    return _module("logic_editor_under_test",
                   company / "company/agents/logic/editor.py")


def _ctx():
    return {"mode": "normal", "day": "wed", "date": "2026-08-26", "memory": "none",
            "hallway": "none", "input": None, "prompt": "You are the site agent."}


def _answering(*replies):
    seen, queue = [], list(replies)

    def chat(system, user, want_json=False, root=None):
        seen.append(user)
        return json.dumps(queue.pop(0) if len(queue) > 1 else queue[0])
    chat.seen = seen
    return chat


def _edit(files, rationale="A small, reversible improvement to the page."):
    return {"files": files, "rationale": rationale, "hallway": None}


# --- the two rewrites that actually happened -------------------------------

def test_the_rewrite_that_took_the_site_down_is_refused():
    """2026-08-26: a quote became an escape, the file grew, the site went dark."""
    assert _validate().check("site/app.js", BROKEN_JS_LINE + "\n")


def test_a_rule_that_forgot_what_it_applies_to_is_refused():
    """2026-08-25: ":root{" became "{" and the stylesheet kept its brace count."""
    v = _validate()
    good = ":root{--bg:#0f1117}\nbody{background:var(--bg)}\n"
    bad = "{--bg:#0f1117}\nbody{background:var(--bg)}\n"
    assert v.check("site/style.css", good) is None
    assert v.check("site/style.css", bad)


def test_a_backslash_in_front_of_a_quote_is_refused():
    """The same rewrite turned "Segoe UI" into \\"Segoe UI\\" — legal, never meant."""
    v = _validate()
    assert v.check("site/style.css", ':root{font-family:"Segoe UI",sans-serif}') is None
    assert v.check("site/style.css", ':root{font-family:\\"Segoe UI\\",sans-serif}')


# --- the guard must not stand in the way of the work -----------------------

@pytest.mark.parametrize("path,text", [
    ("site/app.js", "const a=1/2, b=[1,2].map(x=>x/2), re=/ab\\/c/g;\n"
                    "console.log(`a ${b.join(\"/\")} z`);\n"),
    ("site/app.js", "function f(a,b){ return `${a?`<i>${b}</i>`:''}` }\n"),
    ("site/style.css", "@media (max-width:480px){ header{padding:0} }\n"),
    ("site/style.css", ".a::after{content:'{'}\n"),
    ("site/page.html", "<main><p>one<li>a<li>b</main>\n"),
    ("company/agents/appearance.json", '{"designer": {"top": "cobalt"}}\n'),
    ("company/agents/prompts/webdev.md", "Anything at all. Prose is not parsed.\n"),
])
def test_ordinary_work_passes(path, text):
    """A guard that blocks the work it guards is not a guard."""
    assert _validate().check(path, text) is None


def test_every_file_the_company_ships_parses():
    """Nothing that fails this fence may sit in main, whoever put it there."""
    targets = sorted(
        list((ROOT / "site").glob("*.js")) + list((ROOT / "site").glob("*.css"))
        + list((ROOT / "site").glob("*.html"))
        + [p for p in (ROOT / "company").rglob("*.json")])
    assert len(targets) > 10, "the site and the company data should both be in here"
    broken = {p.relative_to(ROOT).as_posix(): _validate().check(p.name, p.read_text(
        encoding="utf-8")) for p in targets}
    assert not {k: v for k, v in broken.items() if v}


# --- and the editor has to act on it ---------------------------------------

def test_the_editor_refuses_a_rewrite_that_does_not_parse(company):
    editor = _editor(company)
    target = company / "site/app.js"
    before = target.read_text(encoding="utf-8")
    # Long enough to clear SHRINK_FLOOR, so the only thing that can catch it is
    # the parse. This is exactly the shape of the rewrite that merged.
    broken = before.replace(before.splitlines()[7], BROKEN_JS_LINE, 1)
    assert len(broken) > len(before) * editor.SHRINK_FLOOR
    chat = _answering(_edit({"site/app.js": broken}))
    with pytest.raises(ValueError, match="does not parse"):
        editor.run(AGENT, _ctx(), chat, company)
    assert target.read_text(encoding="utf-8") == before


def test_the_editor_refuses_a_stylesheet_that_lost_its_selector(company):
    editor = _editor(company)
    target = company / "site/style.css"
    before = target.read_text(encoding="utf-8")
    chat = _answering(_edit({"site/style.css": before.replace(":root{", "{", 1)}))
    with pytest.raises(ValueError, match="does not parse"):
        editor.run(AGENT, _ctx(), chat, company)
    assert target.read_text(encoding="utf-8") == before


def test_the_editor_refuses_data_that_is_not_json(company):
    """An area can be a data file — the wardrobe — and half a rewrite is not one."""
    editor = _editor(company)
    agent = dict(AGENT, id="designer",
                 alan=["company/agents/appearance.json", "site/"])
    target = company / "company/agents/appearance.json"
    before = target.read_text(encoding="utf-8")
    chat = _answering(_edit({"company/agents/appearance.json": before[:len(before) - 3]}))
    with pytest.raises(ValueError):
        editor.run(agent, _ctx(), chat, company)
    assert target.read_text(encoding="utf-8") == before


def test_a_broken_rewrite_is_told_what_broke_before_it_tries_again(company):
    """The model can correct a fault it can read. It cannot correct silence."""
    editor = _editor(company)
    css = (company / "site/style.css").read_text(encoding="utf-8")
    chat = _answering(_edit({"site/style.css": css.replace(":root{", "{", 1)}),
                      _edit({"site/style.css": css + ".quiet{opacity:.8}\n"}))
    result = editor.run(AGENT, _ctx(), chat, company)
    assert result["files"]["site/style.css"].endswith(".quiet{opacity:.8}\n")
    assert len(chat.seen) == 2
    assert "rejected" in chat.seen[1] and "does not parse" in chat.seen[1]


def test_an_honest_edit_to_the_script_still_goes_through(company):
    """The whole point of the fence is that the work carries on inside it."""
    editor = _editor(company)
    js = (company / "site/app.js").read_text(encoding="utf-8")
    chat = _answering(_edit({"site/app.js": js + "\n/* a quiet note */\n"}))
    result = editor.run(AGENT, _ctx(), chat, company)
    assert result["files"]["site/app.js"].endswith("/* a quiet note */\n")
