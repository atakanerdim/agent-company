"""Does a file the agent just wrote still parse?

On 2026-08-19 an editor handed back two thirds of site/app.js and the site went
dark for three days. The fence built then measured *size*: a rewrite may not drop
below SHRINK_FLOOR of the file. On 2026-08-26 the same page went dark again and
that fence never fired, because the file did not shrink — it grew by 252 bytes.
The damage was one character deep:

    const esc=...{"&":"&amp;","<":"&lt;","\\":"&gt;","'":"&quot;"}...
                                          ^ a quote turned into an escape

and a join() call closed with three quotes instead of two, three times over.
Every byte was there; none of it ran.

So the fence here measures the only thing that actually matters about a file an
agent produces: does it still parse. An agent is free to write anything inside
its area that a parser will accept, and nothing that one will not. The rejection
is fed back into the next attempt, so the model reads its own fault rather than
rolling the same dice again.

Two levels, deliberately:

  * A structural scan that always runs. It is a lexer, not a compiler — it tracks
    strings, template literals, comments and regular expressions well enough to
    know when a quote never closes or a brace never balances, which is the whole
    of the observed failure class.
  * `node --check`, when a node binary is on the machine. That is the real parser
    and it catches everything the scan does not. The shifts and CI both run on
    ubuntu images where node is always present; a laptop without node still gets
    the scan. A check that cannot run is skipped rather than faked.
"""
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

CHECKED = (".json", ".js", ".css", ".html")


# --------------------------------------------------------------------------
# JavaScript
# --------------------------------------------------------------------------

def _js_scan(text):
    """Walk the source tracking what it is inside of. Return an error or None."""
    i, n = 0, len(text)
    depth = 0                 # {} nesting outside strings
    stack = []                # open template literals, for ${ } nesting
    line = 1
    # A slash starts a regular expression rather than a division when the last
    # meaningful thing before it cannot end an expression. This is the standard
    # heuristic and it is enough: the alternative, treating every slash as
    # division, misreads the regexes this file is full of.
    prev = ""

    def fail(msg, at):
        return f"line {at}: {msg}"

    while i < n:
        c = text[i]
        if c == "\n":
            line += 1
            i += 1
            continue
        if c in " \t\r":
            i += 1
            continue

        # comments
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            j = text.find("\n", i)
            i = n if j == -1 else j
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            j = text.find("*/", i + 2)
            if j == -1:
                return fail("a /* comment is never closed", line)
            line += text.count("\n", i, j)
            i = j + 2
            continue

        # regular expression literal
        if c == "/" and prev not in (")", "]", "}") and not (prev.isalnum() or prev in "_$"):
            j, start = i + 1, line
            while j < n:
                d = text[j]
                if d == "\\":
                    j += 2
                    continue
                if d == "\n":
                    return fail("a regular expression is never closed", start)
                if d == "[":                      # a / inside a class is literal
                    while j < n and text[j] != "]":
                        j += 2 if text[j] == "\\" else 1
                if d == "/":
                    break
                j += 1
            if j >= n:
                return fail("a regular expression is never closed", start)
            i = j + 1
            while i < n and text[i].isalpha():    # flags
                i += 1
            prev = "/"
            continue

        # quoted strings
        if c in "'\"":
            j, start = i + 1, line
            while j < n and text[j] != c:
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == "\n":
                    return fail(f"a {c}…{c} string is never closed", start)
                j += 1
            if j >= n:
                return fail(f"a {c}…{c} string is never closed", start)
            i = j + 1
            prev = c
            continue

        # template literal
        if c == "`":
            stack.append(depth)
            i += 1
            start = line
            while i < n:
                d = text[i]
                if d == "\\":
                    i += 2
                    continue
                if d == "\n":
                    line += 1
                    i += 1
                    continue
                if d == "`":
                    stack.pop()
                    i += 1
                    break
                if d == "$" and i + 1 < n and text[i + 1] == "{":
                    i += 2
                    inner = 1
                    # hand the interpolation back to the main loop by scanning it
                    # here with the same rules, one level down
                    sub_start = i
                    while i < n and inner:
                        e = text[i]
                        if e == "\n":
                            line += 1
                        elif e in "'\"`":
                            q = e
                            i += 1
                            while i < n and text[i] != q:
                                if text[i] == "\\":
                                    i += 1
                                elif text[i] == "\n":
                                    line += 1
                                i += 1
                            if i >= n:
                                return fail("a string inside ${…} is never closed", line)
                        elif e == "{":
                            inner += 1
                        elif e == "}":
                            inner -= 1
                        i += 1
                    if inner:
                        return fail("a ${…} interpolation is never closed",
                                    line - text.count("\n", sub_start, n))
                    continue
                i += 1
            else:
                return fail("a `…` template literal is never closed", start)
            prev = "`"
            continue

        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth < 0:
                return fail("a } closes a block that was never opened", line)
        prev = c
        i += 1

    if stack:
        return "a `…` template literal is never closed"
    if depth:
        return f"{depth} block(s) opened with {{ are never closed"
    return None


def _js_node(text):
    """Ask node, if there is a node. Returns an error, or None when it cannot run."""
    node = shutil.which("node")
    if not node:
        return None
    with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8",
                                     delete=False) as fh:
        fh.write(text)
        tmp = fh.name
    try:
        r = subprocess.run([node, "--check", tmp], capture_output=True, text=True,
                           timeout=30)
        if r.returncode == 0:
            return None
        # node prints the offending line, a caret and then the error; the last
        # SyntaxError line is the part worth handing back to the model.
        lines = [ln.strip() for ln in (r.stderr or "").splitlines() if ln.strip()]
        said = next((ln for ln in lines if "Error" in ln), "node --check failed")
        return said.replace(tmp, "the file")
    except (OSError, subprocess.SubprocessError):
        return None
    finally:
        Path(tmp).unlink(missing_ok=True)


# --------------------------------------------------------------------------
# CSS
# --------------------------------------------------------------------------

def _css(text):
    stripped, i, n = [], 0, len(text)
    while i < n:                              # drop comments first
        if text[i] == "/" and i + 1 < n and text[i + 1] == "*":
            j = text.find("*/", i + 2)
            if j == -1:
                return "a /* comment is never closed"
            stripped.append("\n" * text.count("\n", i, j))
            i = j + 2
            continue
        stripped.append(text[i])
        i += 1
    body = "".join(stripped)

    depth, selector, line = 0, [], 1
    i, n = 0, len(body)
    while i < n:
        c = body[i]
        if c == "\n":
            line += 1
        elif c in "'\"":
            j = i + 1
            while j < n and body[j] != c:
                j += 2 if body[j] == "\\" else 1
            if j >= n:
                return f"line {line}: a {c}…{c} string is never closed"
            selector.append(body[i:j + 1])
            i = j + 1
            continue
        elif c == "{":
            # `:root{` losing its selector is how the stylesheet died on
            # 2026-08-25: braces still balanced, every colour gone.
            if depth == 0 and not "".join(selector).strip():
                return (f"line {line}: a {{ block with no selector in front of it — "
                        "a rule must say what it applies to")
            depth += 1
            selector = []
        elif c == "}":
            depth -= 1
            if depth < 0:
                return f"line {line}: a }} closes a block that was never opened"
            selector = []
        elif c == ";":
            selector = []
        else:
            selector.append(c)
        i += 1

    if depth:
        return f"{depth} block(s) opened with {{ are never closed"
    # A backslash in front of a quote is how "Segoe UI" turned into \"Segoe UI\"
    # in the same rewrite. It is legal CSS and it is never what was meant here.
    if "\\\"" in body or "\\'" in body:
        return ("a backslash in front of a quote — CSS is not JSON, write "
                'the quote plainly: font-family:"Segoe UI"')
    return None


# --------------------------------------------------------------------------
# The whole file as a string
# --------------------------------------------------------------------------

def _escaped_whole_file(text):
    """Did the model hand back a JSON string instead of a file?

    On 2026-09-02 site/office.html arrived as a single 4.8 kB line in which every
    line break was the two characters \\ and n, and every attribute quote was
    \\". Nothing that was watching could see it: the file had not shrunk, every
    tag balanced, and Python's HTML parser reads a backslash as an ordinary
    character. Ten links on the page were dead. The intended change was one
    attribute wide.

    Size asks how much of the file came back. Parsing asks whether it holds
    together. Neither asks the question this failure turns on: is this a file at
    all, or a string that once described one.
    """
    if len(text) < 400:
        return None
    literal, real = text.count("\\n"), text.count("\n")
    if literal >= 3 and real <= 2:
        return (f"the whole file came back on one line, with {literal} line breaks "
                "written out as the two characters \\ and n. That is a JSON string, "
                "not a file. Send the file itself: real line breaks, plain quotes.")
    return None


# --------------------------------------------------------------------------
# HTML
# --------------------------------------------------------------------------

# An attribute value that opens with a backslash-quote. Deliberately narrow: a
# backslash before a quote is ordinary inside an inline <script>, and a fence that
# rejects legitimate work is not a fence. In a tag it is always the same mistake.
_ESCAPED_ATTR = re.compile(r'<[a-zA-Z][^<>]*=\\"')


def _html(text):
    from html.parser import HTMLParser

    if _ESCAPED_ATTR.search(text):
        return ('an attribute quoted with a backslash — HTML is not JSON, write it '
                'plainly: class="feed", not class=\\"feed\\"')

    class P(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.open = []
            self.bad = None

        # Only the containers that swallow the rest of the page when left open are
        # tracked. Being strict about <li> and <p> would reject perfectly good
        # markup, and a guard that blocks the work it guards is not a guard.
        WATCHED = {"script", "style", "html", "head", "body", "main", "header",
                   "section", "article", "table", "pre"}

        def handle_starttag(self, tag, attrs):
            if tag in self.WATCHED:
                self.open.append((tag, self.getpos()[0]))

        def handle_endtag(self, tag):
            if tag not in self.WATCHED:
                return
            for k in range(len(self.open) - 1, -1, -1):
                if self.open[k][0] == tag:
                    del self.open[k]
                    return
            if not self.bad:
                self.bad = f"line {self.getpos()[0]}: </{tag}> closes a tag that was never opened"

    p = P()
    p.feed(text)
    p.close()
    if p.bad:
        return p.bad
    if p.open:
        tag, line = p.open[0]
        return f"line {line}: <{tag}> is never closed"
    return None


# --------------------------------------------------------------------------

def check(path, text):
    """Return a sentence explaining why `text` cannot be `path`, or None."""
    suffix = Path(path).suffix.lower()
    if suffix == ".json":
        try:
            json.loads(text)
        except json.JSONDecodeError as e:
            return f"not valid JSON — {e.msg} at line {e.lineno}, column {e.colno}"
        return None
    if suffix in (".html", ".css", ".js", ".md"):
        escaped = _escaped_whole_file(text)
        if escaped:
            return escaped
    if suffix == ".js":
        return _js_scan(text) or _js_node(text)
    if suffix == ".css":
        return _css(text)
    if suffix == ".html":
        return _html(text)
    return None
