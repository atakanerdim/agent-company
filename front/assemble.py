"""Publish the firm's site.

    python front/assemble.py <out dir>

Runs in the publishing workflow after site/build.py, on every change that reaches main.
It reads the firm's own records (company/data, site/data, the git log), computes every
number the pages show, writes them into the page templates under front/pages/, and puts
the result in <out dir> together with front/assets/ and the firm's data files.

No number is typed into a page by hand: firm.py computes them from the records, and a
check that fails stops the publication, so the site keeps the last good version.
"""
import html, importlib.util, json, os, re, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
FRONT_NOTE = ('The layout of these pages was made by the operator; every number and every quoted line '
              'is filled in from the firms\u2019 own records each time a change merges.')
ROOT = os.path.dirname(HERE)
OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, '_site'))

spec = importlib.util.spec_from_file_location('firm', os.path.join(HERE, 'firm.py'))
firm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(firm)


def page(tpl, out_name, desc, live, nav, folio):
    """One page: a template (<title>, <helmet>, <x-dc> body, logic script) to plain HTML."""
    title = re.search(r'<title>(.*?)</title>', tpl, re.S).group(1)
    helmet = re.search(r'<helmet>(.*?)</helmet>', tpl, re.S).group(1).strip()
    body = re.search(r'<x-dc>(.*?)</x-dc>', tpl, re.S).group(1)
    script = re.search(r'(<script type="text/x-dc".*?</script>)', tpl, re.S).group(1)

    # The same header on every page: the firm's navigation and the live line.
    body, n = re.subn(r'<ul class="nav">.*?</ul>', lambda m: nav(out_name), body, count=1, flags=re.S)
    if n != 1:
        raise SystemExit('no navigation in ' + out_name)
    body, n = re.subn(r'<p class="live"[^>]*>.*?</p>', firm.LIVE_LINE, body, count=1, flags=re.S)
    if n != 1:
        raise SystemExit('no live line in ' + out_name)
    # The title block at the foot of the page: every field from the records.
    for label, value in folio.items():
        body, n = re.subn(r'(<span class="tb-l">%s</span><span class="tb-v[^>]*>)([^<]*)' % re.escape(label),
                          lambda m: m.group(1) + html.escape(value), body)
        if n == 0 and label not in firm.TB_OPTIONAL:
            raise SystemExit('title block field %r missing in %s' % (label, out_name))
    body = re.sub(r'(merged, as of )\d{1,2} \w{3} \d{4}', lambda m: m.group(1) + folio.get('As of', ''), body)

    # Footer: the note about who made these pages, and the firms' links (no console any more).
    body, n = re.subn(r'Content may be wrong\.[^<]*', 'Content may be wrong. ' + FRONT_NOTE, body)
    if n != 1:
        raise SystemExit('footer note expected once in %s, found %d' % (out_name, n))
    for repo, label in (('agent-capital', 'Crestpoint'), ('agent-company', 'QuantumPulse')):
        body = re.sub(r'<a href="https://atakanerdim\.github\.io/%s/console/">[^<]*</a>' % repo,
                      '<a href="https://atakanerdim.github.io/%s/">%s</a>' % (repo, label), body)
    if re.search(r'href="[^"]*console/', body):
        raise SystemExit('a link to the retired console is left in ' + out_name)
    unresolved = re.findall(r'__[A-Z0-9_]+__', body + script)
    if unresolved:
        raise SystemExit('unresolved %s in %s' % (sorted(set(unresolved)), out_name))
    data = json.dumps(live, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    url = firm.URL + ('' if out_name == 'index.html' else out_name)
    d = html.escape(desc, quote=True)
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{d}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{firm.NAME}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{d}">
<meta property="og:image" content="{firm.URL}assets/og.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="{firm.THEME}">
<link rel="canonical" href="{url}">
<link rel="icon" href="assets/icon.svg" type="image/svg+xml">
<link rel="stylesheet" href="assets/fonts.css">
{helmet}
<script>window.LIVE={data};</script>
<script src="assets/preact.min.js" defer></script>
<script src="assets/dc.js" defer></script>
</head>
<body>
<div id="dc-root"></div>
<template id="dc-tpl">{body}</template>
{script}
</body>
</html>
'''


def main():
    site = firm.build(ROOT)          # {'pages': [...], 'redirects': {...}}
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    shutil.copytree(os.path.join(HERE, 'assets'), os.path.join(OUT, 'assets'))
    # The firm's records, as the agents' own build published them.
    shutil.copytree(os.path.join(ROOT, 'site', 'data'), os.path.join(OUT, 'data'))
    for p in site['pages']:
        out = page(p['tpl'], p['out'], p['desc'], p['live'], site['nav'], p['folio'])
        open(os.path.join(OUT, p['out']), 'w', encoding='utf-8').write(out)
        print('page', p['out'], len(out))
    nf = open(os.path.join(HERE, '404.html'), encoding='utf-8').read()
    nf = nf.replace('__BASE__', firm.BASE).replace('__MAP__', json.dumps(site['redirects']))
    open(os.path.join(OUT, '404.html'), 'w', encoding='utf-8').write(nf)
    open(os.path.join(OUT, 'robots.txt'), 'w').write('User-agent: *\nAllow: /\n')
    # The teaser the other firm's pages show for this one ("Next door").
    json.dump(site['summary'], open(os.path.join(OUT, 'summary.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    print('published to', OUT)


if __name__ == '__main__':
    main()
