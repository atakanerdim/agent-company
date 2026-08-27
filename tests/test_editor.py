"""The editor rewrites whole files, so a bad answer does not edit a file — it deletes it.

On 2026-08-19 the site agent was shown the first 5000 characters of a 12900-character
site/app.js and asked for the file's full new content. It returned exactly what it had
been shown, cut off mid-word, and the pull request merged: the accuracy table, the
predictions page, the review threads, the minutes and the changelog all went. The same
answer replaced site/style.css with the sentence "/* No changes needed */", and the site
lost every rule of its stylesheet. Nothing in the tests looked at either file, so CI was
green the whole way.

These tests hold the two edges of the fix: a file is never shown in part, and a rewrite
may not collapse the file it replaces.
"""
import importlib.util, json, sys
import pytest

AGENT = {"id": "webdev", "ad": "Kiran Menon", "rol": "site", "logic": "editor",
         "alan": ["site/"], "gunler": ["wed", "sat"], "draft_pr": False}


def _editor(company):
    path = company / "company/agents/logic/editor.py"
    spec = importlib.util.spec_from_file_location("logic_editor_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _ctx():
    return {"mode": "normal", "day": "wed", "date": "2026-08-19", "memory": "none",
            "hallway": "none", "input": None, "prompt": "You are the site agent."}


def _answering(*replies):
    """A chat stub that replies in turn and records every prompt it was given."""
    seen, queue = [], list(replies)
    def chat(system, user, want_json=False, root=None):
        seen.append(user)
        return json.dumps(queue.pop(0) if len(queue) > 1 else queue[0])
    chat.seen = seen
    return chat


def _edit(company, files, rationale="A small, reversible improvement to the page."):
    return {"files": files, "rationale": rationale, "hallway": None}


def test_a_rewrite_may_not_collapse_the_file_it_replaces(company):
    """The real failure: two thirds of app.js returned as the whole of app.js."""
    editor = _editor(company)
    whole = (company / "site/app.js").read_text(encoding="utf-8")
    chat = _answering(_edit(company, {"site/app.js": whole[:len(whole) // 3]}))
    with pytest.raises(ValueError, match="may not drop below"):
        editor.run(AGENT, _ctx(), chat, company)
    assert (company / "site/app.js").read_text(encoding="utf-8") == whole


def test_a_note_about_the_file_is_not_the_file(company):
    """style.css came back as the four words "/* No changes needed */"."""
    editor = _editor(company)
    before = (company / "site/style.css").read_text(encoding="utf-8")
    chat = _answering(_edit(company, {"site/style.css": "/* No changes needed */"}))
    with pytest.raises(ValueError, match="may not drop below"):
        editor.run(AGENT, _ctx(), chat, company)
    assert (company / "site/style.css").read_text(encoding="utf-8") == before


def test_every_file_offered_for_rewrite_is_shown_whole(company):
    """Ask for a file's last line and you must have been given its last line."""
    editor = _editor(company)
    chat = _answering(_edit(company, {"site/new-note.css": "/* a new file */\n"}))
    editor.run(AGENT, _ctx(), chat, company)
    shown = chat.seen[0]
    for name in ("app.js", "style.css"):
        body = (company / "site" / name).read_text(encoding="utf-8")
        assert len(body) <= editor.CONTENT_LIMIT, f"{name} no longer fits; raise the limit"
        assert body.rstrip()[-40:] in shown, f"{name} was cropped before the agent saw it"


def test_a_file_too_long_to_show_is_marked_and_cannot_be_rewritten(company):
    editor = _editor(company)
    long_file = company / "site/long.css"
    long_file.write_text("/* x */\n" * (editor.CONTENT_LIMIT // 4), encoding="utf-8")
    before = long_file.read_text(encoding="utf-8")
    chat = _answering(_edit(company, {"site/long.css": "/* rewritten */\n"}))
    with pytest.raises(ValueError, match="in part only"):
        editor.run(AGENT, _ctx(), chat, company)
    assert "TOO LONG TO REWRITE" in chat.seen[0]
    assert long_file.read_text(encoding="utf-8") == before


def test_an_honest_edit_still_goes_through(company):
    """The guard must not stand in the way of the work it exists to protect."""
    editor = _editor(company)
    css = (company / "site/style.css").read_text(encoding="utf-8")
    chat = _answering(_edit(company, {"site/style.css": css + ".quiet{opacity:.8}\n"}))
    result = editor.run(AGENT, _ctx(), chat, company)
    assert result["files"]["site/style.css"].endswith(".quiet{opacity:.8}\n")
    assert result["pr"]["title"] == "webdev: edit 2026-08-19"
    assert result["pr"]["draft"] is False


def test_a_rejected_answer_is_told_why_before_it_tries_again(company):
    """Three rolls of the same dice is not a retry; the model has to read the fault."""
    editor = _editor(company)
    css = (company / "site/style.css").read_text(encoding="utf-8")
    chat = _answering(_edit(company, {"site/style.css": "/* No changes needed */"}),
                      _edit(company, {"site/style.css": css + ".quiet{opacity:.8}\n"}))
    result = editor.run(AGENT, _ctx(), chat, company)
    assert result["files"]["site/style.css"].endswith(".quiet{opacity:.8}\n")
    assert len(chat.seen) == 2
    assert "rejected" in chat.seen[1] and "may not drop below" in chat.seen[1]
    assert "rejected" not in chat.seen[0]


def test_a_file_the_editor_never_saw_cannot_be_rewritten(company):
    """The area can outgrow the sample, and then a file is edited blind.

    SAMPLE_FILE_LIMIT caps how many files go into the prompt. Files past the cap
    used to be dropped in silence, which leaves the agent free to hand back a file
    it was never shown — the same way site/app.js was lost, only without even a
    truncated copy to work from.
    """
    editor = _editor(company)
    for n in range(editor.SAMPLE_FILE_LIMIT + 4):
        (company / f"site/filler-{n:02d}.css").write_text(f"/* {n} */\n", encoding="utf-8")
    shown, unrewritable = editor._current(company, AGENT["alan"])
    hidden = [rel for rel, why in unrewritable.items() if "not shown to you this time" in why]
    assert hidden, "the area must overflow the sample for this test to mean anything"
    target = hidden[0]
    assert f"--- {target} ---" not in shown, "a hidden file must not appear in the prompt"
    before = (company / target).read_text(encoding="utf-8")

    chat = _answering(_edit(company, {target: "/* rewritten blind */\n"}))
    with pytest.raises(ValueError, match="not shown to you this time"):
        editor.run(AGENT, _ctx(), chat, company)
    assert (company / target).read_text(encoding="utf-8") == before
    assert "DO NOT REWRITE" in chat.seen[0]


def test_the_window_turns_so_no_file_is_unreachable_for_good(company):
    """A large area must not strand most of itself behind the sample limit.

    The Process Owner tends twelve prompts and twelve memories. Showing the same
    first eight every week would leave the rest permanently unwritable — the guard
    would have replaced one silent failure with another. The window turns instead:
    what is shown may be rewritten, and everything is shown eventually.
    """
    editor = _editor(company)
    area = ["company/agents/prompts/"]
    total = len(list((company / "company/agents/prompts").glob("*.md")))
    assert total > editor.SAMPLE_FILE_LIMIT, "this area is meant to overflow the sample"

    seen = set()
    windows = []
    for seed in range(total):
        shown, unrewritable = editor._current(company, area, seed)
        window = frozenset(rel for rel in
                           (p.relative_to(company).as_posix()
                            for p in (company / "company/agents/prompts").glob("*.md"))
                           if rel not in unrewritable)
        assert len(window) == editor.SAMPLE_FILE_LIMIT
        windows.append(window)
        seen |= window
    assert len(seen) == total, f"{total - len(seen)} file(s) never came round"
    assert len(set(windows)) > 1, "the window never actually turned"


def test_what_is_shown_this_shift_is_what_may_be_rewritten(company):
    """The rule does not change with the window: only a file in front of you."""
    editor = _editor(company)
    area = ["company/agents/prompts/"]
    _, unrewritable = editor._current(company, area, 3)
    blocked = sorted(unrewritable)[0]
    before = (company / blocked).read_text(encoding="utf-8")
    agent = dict(AGENT, id="process", alan=area)
    chat = _answering(_edit(company, {blocked: "# replaced\n"}))
    ctx = dict(_ctx(), date="2026-08-25")
    with pytest.raises(ValueError):
        editor.run(agent, ctx, chat, company)
    assert (company / blocked).read_text(encoding="utf-8") == before


def test_a_file_of_another_kind_cannot_be_rewritten_blind(company):
    """The sample only ever offers text files, and the guard only covered those.

    "What is shown may be rewritten" was half a rule. The sample is built from
    .css .html .js .md .json, so anything else in the area — site/build.py, which
    generates the entire site — was never a candidate, never marked unrewritable,
    and could be handed back whole by an agent that had not seen a line of it.
    Confirmed by hand on 2026-08-27: a 4800-character replacement for a 4455-character
    build.py cleared SHRINK_FLOOR and was accepted.
    """
    editor = _editor(company)
    target = company / "site/build.py"
    before = target.read_text(encoding="utf-8")
    # Long enough to clear the shrink floor, so nothing else can catch it.
    blind = "# rewritten blind\n" + ("x = 1\n" * 1200)
    assert len(blind) > len(before) * editor.SHRINK_FLOOR
    chat = _answering(_edit(company, {"site/build.py": blind}))
    with pytest.raises(ValueError, match="not one of the files you were shown"):
        editor.run(AGENT, _ctx(), chat, company)
    assert target.read_text(encoding="utf-8") == before
    assert "site/build.py" not in chat.seen[0], "an unshown file must not be in the prompt"


def test_build_output_is_not_a_place_to_write(company):
    """site/data/ is regenerated on every deploy, so writing there is writing to nothing."""
    editor = _editor(company)
    chat = _answering(_edit(company, {"site/data/roster.json": '[{"id": "ceo"}]'}))
    with pytest.raises(ValueError, match="build output"):
        editor.run(AGENT, _ctx(), chat, company)


def test_a_new_file_is_still_allowed(company):
    """Only overwriting an unseen file is barred. Creating one was never the problem."""
    editor = _editor(company)
    chat = _answering(_edit(company, {"site/new-note.css": "/* a brand new file */\n"}))
    result = editor.run(AGENT, _ctx(), chat, company)
    assert "site/new-note.css" in result["files"]
