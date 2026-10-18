"""Staff and Log pages, computed from the firm's own records on every publication.

    build(root, firm_code, ctx) -> {'staff.html': template, 'log.html': template}

firm_code is 'CP' (Crestpoint, agent-capital) or 'QP' (QuantumPulse, agent-company).
The look comes from the two base templates in front/pages/ (staff.dc.html, log.dc.html,
or ctx['base_dir']); this module replaces every part of them that depends on the
records: the people, their latest words and work, the shift roster, the change feed and
the maintenance list. Nothing is typed in by hand.

ctx keys:
  as_of_iso  ISO date (or datetime) of the last merge; nothing after it is shown.
  as_of      the same date for display, e.g. "16 Oct 2026".
  leave      {agent id: 'YYYY-MM-DD'} for colleagues on leave (optional).
  base_dir   folder holding staff.dc.html and log.dc.html (optional).
  foot_note  replaces the operator sentence at the end of the footer text (optional).
"""
import html, json, math, os, re, subprocess

E = lambda s: html.escape(s, quote=True)
MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
WEEK = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
WD = {'mon': 'Mon', 'tue': 'Tue', 'wed': 'Wed', 'thu': 'Thu', 'fri': 'Fri', 'sat': 'Sat', 'sun': 'Sun'}
NUM = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve']

FIRMS = {
    'CP': dict(name='Crestpoint Analytics', short='Crestpoint', repo='agent-capital', folder='crestpoint',
               other_repo='agent-company', other_name='QuantumPulse Analytics', other_short='QuantumPulse',
               default='desk', ghost_sub='The desk’s ghost. Hasn’t made a decision since 9 September.'),
    'QP': dict(name='QuantumPulse Analytics', short='QuantumPulse', repo='agent-company', folder='quantumpulse',
               other_repo='agent-capital', other_name='Crestpoint Analytics', other_short='Crestpoint',
               default='scrum', ghost_sub='The studio’s ghost. Has never watched a match.'),
}
WORKS = {
    'CP': {
        'desk': 'Prices, books and standings, every weekday.',
        'evaluator': 'The Friday review of every book.',
        'chief': 'The Sunday letter, and once a month the rewrite.',
        '_advisor': 'One book of nine, started with the same imaginary $100,000.',
    },
    'QP': {
        'ceo': 'The weekly report, every Sunday.',
        'scrum': 'The list of what got stuck this week.',
        'process': 'Her colleagues’ working instructions, after every retro.',
        'analyst': 'Fixtures on Thursday, results on Monday.',
        'statistician': 'A score for every match in the five big leagues, every Friday.',
        'romantic': 'A score for every match in the five big leagues, every Friday.',
        'coolhead': 'A score for every match in the five big leagues, every Friday.',
        'evaluator': 'Scoring the week and writing the retro, every Monday.',
        'pessimist': 'The Friday critique of everyone else’s work.',
        'gossip': 'The hallway gazette, every Wednesday.',
        'designer': 'The site’s look and the staff’s wardrobe.',
        'webdev': 'The site’s pages, on Wednesdays and Saturdays.',
    },
}
# The studio's job titles, in the words the rest of the site uses.
ROLE_FIX = {
    'QP': {
        'analyst': 'Analyst: fixtures and results',
        'statistician': 'Predictor, the statistician',
        'romantic': 'Predictor, the romantic',
        'coolhead': 'Predictor, the cool head',
        'evaluator': 'Evaluator: scoring and retro',
        'gossip': 'Hallway gazette',
    },
}


def dt(iso):
    y, m, d = iso[:10].split('-')
    return '%d %s %s' % (int(d), MON[int(m) - 1], y)


def days(ds):
    ds = sorted(ds, key=WEEK.index)
    if ds == WEEK[:5]:
        return 'Mon to Fri'
    names = [WD[d] for d in ds]
    return names[0] if len(names) == 1 else ', '.join(names[:-1]) + ' and ' + names[-1]


def strip_name(text, name):
    t = text.strip()
    while t.startswith(name + ':'):
        t = t[len(name) + 1:].strip()
    return t


def load(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def money(v):
    return '${:,.0f}'.format(v) if abs(v - round(v)) < 0.005 else '${:,.2f}'.format(v)


# ---------------------------------------------------------------- the records

def collect(root, code, cut):
    F = FIRMS[code]
    roster = load(os.path.join(root, 'company/roster.json'))
    ident = {x['id']: x for x in load(os.path.join(root, 'company/agents/identity.json'))}
    names = {a['id']: a['ad'] for a in roster}
    hall = {}
    hdir = os.path.join(root, 'company/hallway')
    for fn in sorted(os.listdir(hdir)) if os.path.isdir(hdir) else []:
        m = re.match(r'(\d{4}-\d{2}-\d{2})-([a-z]+)\.txt$', fn)
        if not m or m.group(1) > cut:
            continue
        txt = open(os.path.join(hdir, fn), encoding='utf-8').read().strip()
        if txt:
            hall[m.group(2)] = {'date': m.group(1), 'text': txt}
    out = subprocess.run(['git', '-C', root, 'log', '--format=%h|%ad|%s', '--date=short'],
                         capture_output=True, text=True, check=True).stdout.strip()
    prs, ops = [], []
    for line in out.split('\n') if out else []:
        h, d, s = line.split('|', 2)
        m = re.search(r'\s*\(#(\d+)\)$', s)
        if not m:
            ops.append({'h': h, 'date': d, 'msg': s})
            continue
        body = s[:m.start()]
        pre, _, rest = body.partition(': ')
        who = rest.split(' ')[0] if pre == 'predictions' else pre
        prs.append({'n': int(m.group(1)), 'date': d, 'pre': pre, 'who': who, 'title': body})
    if not prs:
        raise SystemExit('staff_log: no merged pull requests found in the git log (shallow clone?)')
    staff = []
    for a in roster:
        i = ident.get(a['id'], {})
        mine = [p for p in prs if p['who'] == a['id']]
        staff.append({'id': a['id'], 'name': a['ad'], 'title': i.get('title') or a.get('rol', ''),
                      'room': i.get('room') or '', 'bio': i.get('bio') or '', 'days': a.get('gunler') or [],
                      'said': hall.get(a['id']), 'work': mine[0] if mine else None})
    return {'staff': staff, 'prs': prs, 'ops': ops, 'names': names}


def cp_orders(root, cut):
    """The latest orders file up to the cut: {advisor: entry}, plus its date."""
    odir = os.path.join(root, 'company/data/orders')
    files = sorted(f for f in os.listdir(odir) if re.match(r'\d{4}-\d{2}-\d{2}\.json$', f) and f[:10] <= cut)
    if not files:
        return None, {}
    return files[-1][:10], load(os.path.join(odir, files[-1])).get('advisors', {})


def cp_order_line(entry, date):
    when = entry.get('decided_utc') or ''
    hm = when[11:16] if len(when) >= 16 else ''
    stamp = ('%s UTC, %s' % (hm, dt(date))) if hm else dt(date)
    filled, refused = entry.get('orders') or [], entry.get('rejected') or []
    def one(o):
        return '%s %s, %s' % ((o.get('action') or '').capitalize(), o.get('instrument', ''), money(float(o.get('amount_usd') or 0)))
    if filled:
        more = len(filled) - 1
        line = '%s%s. Filled, %s.' % (one(filled[0]), (', and %d more' % more) if more else '', stamp)
        if refused:
            line += ' %s refused by the risk code.' % ('One more' if len(refused) == 1 else '%s more' % NUM[min(len(refused), 12)].capitalize())
        return line
    if refused:
        return '%s. Refused by the risk code, %s.' % (one(refused[0].get('order', {})), stamp)
    return 'No orders placed, %s. Held.' % dt(date)


def latest_minutes(root, cut, agent):
    mdir = os.path.join(root, 'company/minutes')
    fs = sorted(f for f in os.listdir(mdir) if f.endswith('-%s.md' % agent) and f[:10] <= cut) if os.path.isdir(mdir) else []
    return fs[-1] if fs else None


# ---------------------------------------------------------------- people

def wavy(cx, cy, r, a, n, ph, steps):
    pts = []
    for i in range(steps):
        t = 2 * math.pi * i / steps
        rr = r + a * math.sin(n * t + ph)
        pts.append('%.1f %.1f' % (cx + rr * math.cos(t), cy + rr * math.sin(t)))
    return 'M' + ' L'.join(pts) + ' Z'


def ring_svg(code):
    if code == 'QP':
        return '<svg viewBox="0 0 88 88" aria-hidden="true"><circle class="ring" pathLength="1" cx="44" cy="44" r="41"></circle><path class="lead" pathLength="1" d="M85 44 H100"></path></svg>'
    paths = ''.join('<path class="gr gr%d" pathLength="1" d="%s"></path>' % (k, wavy(44, 44, 40.2, 2.1, 18, 2 * math.pi * k / 3, 144)) for k in range(3))
    return '<svg viewBox="0 0 88 88" aria-hidden="true"><circle class="gr-o" cx="44" cy="44" r="43.2"></circle>%s<circle class="gr-i" cx="44" cy="44" r="36.6"></circle><path class="lead" pathLength="1" d="M87 44 H100"></path></svg>' % paths


def people(root, code, D, cut, leave):
    F = FIRMS[code]
    gh = 'https://github.com/atakanerdim/%s' % F['repo']
    odate, orders = cp_orders(root, cut) if code == 'CP' else (None, {})
    out = []
    for s in D['staff']:
        pid = s['id']
        role = ROLE_FIX.get(code, {}).get(pid) or (s['title'][:1] + s['title'][1:].lower())
        works = WORKS[code].get(pid) or WORKS[code].get('_advisor') or ''
        said = s['said']
        said_txt = strip_name(said['text'], s['name']) if said else ''
        said_when = ('Hallway, %s. Agent writing.' % dt(said['date'])) if said else ''
        if code == 'CP' and pid == 'evaluator':
            mf = latest_minutes(root, cut, 'evaluator')
            work = ('Weekly review, %s.' % dt(mf[:10])) if mf else 'No weekly review yet.'
            work_url = ('%s/blob/main/company/minutes/%s' % (gh, mf)) if mf else gh
            work_when = 'In the minutes.'
        elif s['work'] is not None:
            w = s['work']
            work = '#%d %s' % (w['n'], w['title'])
            work_url = '%s/pull/%d' % (gh, w['n'])
            work_when = 'Merged %s. Approved by nobody.' % dt(w['date'])
        elif code == 'CP' and pid in orders:
            work = cp_order_line(orders[pid], odate)
            work_url = '%s/blob/main/company/data/orders/%s.json' % (gh, odate)
            work_when = 'From the orders file, %s.' % dt(odate)
        else:
            work, work_url, work_when = 'Nothing merged yet.', gh + '/pulls?q=is%3Amerged', ''
        on_leave = leave.get(pid)
        shift = ('On leave since %s' % dt(on_leave)) if on_leave else (('On shift: %s' % days(s['days'])) if s['days'] else 'Off the roster')
        out.append({
            'id': pid, 'name': s['name'], 'role': role, 'room': s['room'], 'dayset': [] if on_leave else s['days'],
            'shift': shift, 'days': days(s['days']) if s['days'] else '', 'bio': s['bio'], 'works': works,
            'img': 'assets/portraits/%s/%s.svg' % (F['folder'], pid),
            'brief': '%s/blob/main/company/agents/prompts/%s.md' % (gh, pid),
            'briefPath': 'company/agents/prompts/%s.md' % pid,
            'said': said_txt, 'saidWhen': said_when, 'hasSaid': bool(said_txt), 'noSaid': not said_txt,
            'work': work, 'workUrl': work_url, 'workWhen': work_when,
        })
    return out


def sub1(pattern, repl, s, what, flags=re.S):
    out, n = re.subn(pattern, lambda m: repl if not callable(repl) else repl(m), s, count=1, flags=flags)
    if n != 1:
        raise SystemExit('staff_log: could not find %s in the base template' % what)
    return out


def footer_links(s, code, ctx):
    """The console is retired: the firm's own site is this one, the other firm's is linked."""
    F = FIRMS[code]
    links = '\n'.join('<a href="%s">%s</a>' % x for x in [
        ('https://github.com/atakanerdim/%s' % F['repo'], '%s on GitHub' % F['short']),
        ('https://atakanerdim.github.io/%s/' % F['other_repo'], F['other_name']),
        ('https://github.com/atakanerdim/%s' % F['other_repo'], '%s on GitHub' % F['other_short']),
    ])
    s = sub1(r'(<div class="foot-links">\n).*?(\n</div>)', lambda m: m.group(1) + links + m.group(2), s, 'footer links')
    if ctx.get('foot_note'):
        s = re.sub(r'(<p class="foot-text">.*?Content may be wrong\.)[^<]*(</p>)',
                   lambda m: m.group(1) + ' ' + E(ctx['foot_note']) + m.group(2), s, count=1, flags=re.S)
    if '/console/' in s:
        raise SystemExit('staff_log: a console link survived')
    return s


TODAY_JS = r'''
var TODAY = (function () {
  var W = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'], D = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  var M = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  var N = ['none', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve'];
  var now = new Date(), wd = W[now.getUTCDay()], day = now.getUTCDate(), mo = now.getUTCMonth(), yr = now.getUTCFullYear();
  var tday = {}, lit = {}, ti = {}, on = [], i = 0;
  ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'].forEach(function (d) { tday[d] = d === wd ? 'today' : ''; });
  TEAM.ids.forEach(function (id) {
    var here = TEAM.days[id].indexOf(wd) >= 0;
    lit[id] = here ? 'lit' : ''; ti[id] = here ? '--i: ' + (i++) : '';
    if (here) on.push(id);
  });
  var names = on.map(function (id) { return TEAM.names[id]; });
  if (TEAM.group && TEAM.group.ids.every(function (id) { return on.indexOf(id) >= 0; })) {
    names = on.filter(function (id) { return TEAM.group.ids.indexOf(id) < 0; }).map(function (id) { return TEAM.names[id]; });
    names.push(TEAM.group.label);
  }
  var list = names.length < 2 ? names.join('') : names.slice(0, -1).join(', ') + ' and ' + names[names.length - 1];
  var dateLong = D[now.getUTCDay()] + ' ' + day + ' ' + M[mo] + ' ' + yr;
  var n = on.length, total = TEAM.ids.length - TEAM.away;
  var line = n === 0 ? 'On ' + dateLong + ', nobody is on shift.'
    : 'On ' + dateLong + ', ' + N[n] + ' of ' + N[total] + (n === 1 ? ' is' : ' are') + ' on shift: ' + list + '.';
  if (TEAM.away) line += ' ' + TEAM.awayLine;
  return { tday: tday, lit: lit, ti: ti, line: line, long: dateLong,
           stamp: D[now.getUTCDay()].slice(0, 3) + ' ' + day + ' ' + M[mo].slice(0, 3) + ' ' + yr };
})();
'''


def staff_page(base, root, code, D, ctx, cut):
    F = FIRMS[code]
    leave = ctx.get('leave') or {}
    P = people(root, code, D, cut, leave)
    s = base
    # the people, room by room, in the order the rooms first appear
    rooms, groups = [], {}
    for p in P:
        if p['room'] not in groups:
            rooms.append(p['room'])
        groups.setdefault(p['room'], []).append(p)
    ring = ring_svg(code)
    parts = []
    for room in rooms:
        ps = groups[room]
        parts.append('<h3 class="room">%s<small>%s</small></h3>' % (E(room[:1] + room[1:].lower()), 'one colleague' if len(ps) == 1 else '%s colleagues' % NUM[len(ps)]))
        parts.append('<ul class="folks">%s</ul>' % ''.join(
            '<li><button type="button" class="who {{ sel.%s }}" aria-pressed="{{ prs.%s }}" onClick="{{ pick.%s }}"><span class="det">%s<img src="%s" width="66" height="66" alt=""></span><span class="plate"><b>%s</b><span>%s</span><span class="dy">%s</span></span></button></li>'
            % (p['id'], p['id'], p['id'], ring, p['img'], E(p['name']), E(p['role']), E(p['shift'])) for p in ps))
    s = sub1(r'(<h2 class="h2" id="s2-h">Personnel sheet</h2>\n).*?(<h3 class="room">The ghost)',
             lambda m: m.group(1) + '\n'.join(parts) + '\n' + m.group(2), s, 'people list')
    s = sub1(r'(<h1 class="h1" id="s1-h">)\w+( colleagues\. None of them people\.</h1>)',
             lambda m: m.group(1) + NUM[len(P)].capitalize() + m.group(2), s, 'headline')
    s = sub1(r'<p class="one-r">On shift: \{\{ cur\.days \}\}</p>', '<p class="one-r">{{ cur.shift }}</p>', s, 'shift line')
    # the roster: who works which day; "today" is decided in the reader's browser (UTC, like the shifts)
    trs = []
    for p in P:
        on = p['dayset']
        cells = []
        for d in WEEK:
            here = d in on
            cells.append('<td class="c%s {{ tday.%s }}"%s><span title="%s, %s"></span></td>' % (
                ' on' if here else '', d, (' style="{{ ti.%s }}"' % p['id']) if here else '', WD[d],
                'on shift' if here else ('on leave' if p['id'] in leave else 'off')))
        trs.append('<tr class="{{ lit.%s }}"><td class="nm"><img src="%s" width="28" height="28" alt="">%s</td>%s</tr>' % (p['id'], p['img'], E(p['name']), ''.join(cells)))
    ths = ''.join('<th scope="col" class="{{ tday.%s }}">%s</th>' % (d, WD[d]) for d in WEEK)
    table = '<table class="roster {{ s3Cls }}" ref="{{ r.s3 }}"><caption class="sr">Who works which day. Today is {{ todayLong }}.</caption><thead><tr><th scope="col">Colleague</th>%s</tr></thead><tbody>%s</tbody></table>' % (ths, ''.join(trs))
    s = sub1(r'<table class="roster .*?</table>', table, s, 'roster table')
    s = sub1(r'(<h2 class="h2" id="s3-h">On shift today</h2><span class="asof">)[^<]*(</span>)',
             lambda m: m.group(1) + '{{ todayStamp }}' + m.group(2), s, 'today stamp')
    s = sub1(r'<p class="lede s3-line">[^<]*</p>', '<p class="lede s3-line">{{ todayLine }}</p>', s, 'today line')
    s = footer_links(s, code, ctx)
    # the logic: data and the roster's "today"
    staff = {p['id']: {k: p[k] for k in ('name', 'role', 'bio', 'works', 'img', 'brief', 'briefPath', 'said', 'saidWhen',
                                         'hasSaid', 'noSaid', 'work', 'workUrl', 'workWhen', 'days', 'shift')} for p in P}
    away = [p for p in P if p['id'] in leave]
    advisors = [p['id'] for p in P if code == 'CP' and p['role'].startswith('Advisor')]
    team = {'ids': [p['id'] for p in P], 'days': {p['id']: p['dayset'] for p in P}, 'names': {p['id']: p['name'] for p in P},
            'away': len(away),
            'awayLine': ('%s %s on leave.' % (' and '.join(p['name'] for p in away), 'is' if len(away) == 1 else 'are')) if away else '',
            'group': {'ids': advisors, 'label': 'the %s advisors' % NUM[len(advisors)]} if len(advisors) > 1 else None}
    default = F['default'] if F['default'] in staff else P[0]['id']
    s = sub1(r'var STAFF = .*?;\nvar IDS = .*?;\n',
             lambda m: 'var STAFF = %s;\nvar IDS = %s;\nvar TEAM = %s;\n%s' % (
                 json.dumps(staff, ensure_ascii=False), json.dumps([p['id'] for p in P]),
                 json.dumps(team, ensure_ascii=False), TODAY_JS), s, 'staff data')
    s = sub1(r"sel: '\w+', s3:", "sel: '%s', s3:" % default, s, 'default selection')
    s = sub1(r"(s3Cls: s\.s3 \? 'go' : '', swapCls: s\.swap \? 'is-swap' : '')",
             lambda m: m.group(1) + ',\n      tday: TODAY.tday, lit: TODAY.lit, ti: TODAY.ti, todayLine: TODAY.line, todayLong: TODAY.long, todayStamp: TODAY.stamp',
             s, 'renderVals return')
    return s


# ---------------------------------------------------------------- log

def log_page(base, root, code, D, ctx, cut):
    F = FIRMS[code]
    gh = 'https://github.com/atakanerdim/%s' % F['repo']
    staff = {x['id']: x for x in D['staff']}
    prs = [p for p in D['prs'] if p['pre'] != 'tests']
    rows, who_names, counts = [], {}, {}
    for p in prs:
        w = p['who']
        if w in staff:
            nm, img = staff[w]['name'], 'assets/portraits/%s/%s.svg' % (F['folder'], w)
        else:
            nm, img = 'Shift log', ''
        who_names[w] = nm
        counts[w] = counts.get(w, 0) + 1
        rows.append({'n': '#%d' % p['n'], 'date': dt(p['date']), 'url': '%s/pull/%d' % (gh, p['n']),
                     'who': w, 'name': nm, 'img': img, 'hasImg': bool(img), 'noImg': not img, 'title': p['title']})
    order = [x['id'] for x in D['staff'] if x['id'] in counts] + [w for w in counts if w not in staff]
    chips = [{'id': 'all', 'name': 'Everyone', 'n': len(rows)}] + [{'id': w, 'name': who_names[w], 'n': counts[w]} for w in order]
    ops = D['ops']
    mt = ''.join('<li><span class="d">%s</span><span>%s</span><a href="%s/commit/%s">%s</a></li>' % (dt(o['date']), E(o['msg']), gh, o['h'], o['h']) for o in ops)
    s = base
    s = sub1(r'(<div class="lg-sub"><p class="lede">)\d+( so far\. Approved by nobody\.</p><span class="asof">)[^<]*(</span>)',
             lambda m: m.group(1) + str(len(rows)) + m.group(2) + 'As of ' + ctx['as_of'] + m.group(3), s, 'feed count')
    s = sub1(r'(Changes the operator made directly: )\d+', lambda m: m.group(1) + str(len(ops)), s, 'maintenance count')
    s = sub1(r'<ol class="mt">.*?</ol>', '<ol class="mt">%s</ol>' % mt, s, 'maintenance list')
    tests = [p for p in D['prs'] if p['pre'] == 'tests']
    extra = ''
    if tests:
        t = tests[-1]
        extra = '<p class="l2-pr">%s from the operator as a pull request, so it passed the same checks as everything else: <a href="%s/pull/%d">#%d</a>, %s, “%s”.</p>' % (
            'One more came' if len(tests) == 1 else '%s more came' % NUM[min(len(tests), 12)].capitalize(), gh, t['n'], t['n'], dt(t['date']), E(t['title']))
    s, n = re.subn(r'<p class="l2-pr">.*?</p>', extra, s, count=1, flags=re.S)
    if n == 0 and extra:
        s = sub1(r'(<ol class="mt">.*?</ol>)', lambda m: m.group(1) + '\n' + extra, s, 'maintenance end')
    s = footer_links(s, code, ctx)
    s = sub1(r'var ROWS = .*?;\nvar CHIPS = .*?;\n',
             lambda m: 'var ROWS = %s;\nvar CHIPS = %s;\n' % (json.dumps(rows, ensure_ascii=False), json.dumps(chips, ensure_ascii=False)),
             s, 'log data')
    return s


# ---------------------------------------------------------------- entry

def build(root, firm_code, ctx):
    if firm_code not in FIRMS:
        raise SystemExit('staff_log: firm code must be CP or QP')
    cut = str(ctx['as_of_iso'])[:10]
    base_dir = ctx.get('base_dir') or os.path.join(root, 'front', 'pages')
    D = collect(root, firm_code, cut)
    staff_base = open(os.path.join(base_dir, 'staff.dc.html'), encoding='utf-8').read()
    log_base = open(os.path.join(base_dir, 'log.dc.html'), encoding='utf-8').read()
    out = {'staff.html': staff_page(staff_base, root, firm_code, D, ctx, cut),
           'log.html': log_page(log_base, root, firm_code, D, ctx, cut)}
    for k, v in out.items():
        if '/_blob/' in v or '.dc.html' in v:
            raise SystemExit('staff_log: a design-tool path survived in ' + k)
    return out
