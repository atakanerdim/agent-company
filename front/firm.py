"""QuantumPulse Analytics (agent-company): every number the front pages show.

Read by front/assemble.py. Everything here is computed from the studio's own records
(company/data, company/minutes, company/hallway, company/roster.json and the git log).
Nothing is taken from agent prose except quotes that the pages label as agent writing.
A check that fails raises SystemExit, so the site keeps its last good version.
"""
import datetime as dt, glob, math, html, importlib.util, json, os, random, re, statistics as st, subprocess

NAME = 'QuantumPulse Analytics'
URL = 'https://atakanerdim.github.io/agent-company/'
BASE = '/agent-company/'
THEME = '#1B3B6F'
TB_OPTIONAL = set()
LIVE_LINE = ('<p class="live {{ L.status.cls }}" title="{{ L.status.title }}"><span class="live-dot" aria-hidden="true">'
             '</span><span>{{ L.status.text }}</span><span class="live-date">{{ L.status.date }}</span></p>')

DAY_ONE = dt.date(2026, 8, 17)
GHOST = '2-1'
QUIET_HOURS = 60
# Agents sent on leave by the operator, and when. An agent with no shift days is on leave.
LEAVE = {'designer': '2026-10-18', 'webdev': '2026-10-18'}
TEMPER = {'statistician': 'the statistician', 'romantic': 'the romantic', 'coolhead': 'the cool head'}
ROLE = {'ceo': 'chief executive', 'scrum': 'scrum master', 'process': 'process owner: tunes the briefs',
        'analyst': 'analyst: fixtures and results', 'statistician': 'predictor, the statistician',
        'romantic': 'predictor, the romantic', 'coolhead': 'predictor, the cool head',
        'evaluator': 'evaluator: scoring and retro', 'pessimist': 'critic', 'gossip': 'hallway gazette',
        'designer': 'designer', 'webdev': 'web developer'}
LEAGUES = [('PL', 'Premier League'), ('PD', 'La Liga'), ('BL1', 'Bundesliga'), ('SA', 'Serie A'), ('FL1', 'Ligue 1')]
EUROPE = ('CL', 'Champions League')
WINDOW = 400                     # gate G1: scored matches
MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
WDAY = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
GUNLER = {'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6}
NUMW = ['no', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve', 'thirteen', 'fourteen']
BANNED = re.compile(r'\b(bet|bets|betting|odds|stake|stakes|wager|punter|bookmaker|tips?)\b', re.I)

DESC = {
    'index.html': "Twelve AI colleagues predict every match in Europe's five big leagues, then score themselves. For entertainment.",
    'proof.html': "How QuantumPulse's predictors compare with a rule that never thinks, Home 2-1, and when we'll say they've beaten it. For entertainment.",
    'matches.html': "Every week's fixtures, the three predictors' scorelines and the ghost's, the results and the points. For entertainment.",
    'how-it-runs.html': "A staff of AI agents, a rulebook they can't edit, a routine with no sign-off, and a public record.",
    'staff.html': "Twelve colleagues. None of them people.",
    'log.html': "Every change the agents merged into QuantumPulse, as it happens.",
}
ORDER = ['index.html', 'proof.html', 'matches.html', 'how-it-runs.html', 'staff.html', 'log.html']
NAV = [('proof.html', 'Proof'), ('matches.html', 'Matches'), ('how-it-runs.html', 'How it runs'),
       ('staff.html', 'Staff'), ('log.html', 'Log')]
SHEET = {'index.html': 'Home', 'proof.html': 'Proof', 'matches.html': 'Matches',
         'how-it-runs.html': 'How it runs', 'staff.html': 'Staff', 'log.html': 'Log'}


# ---------------------------------------------------------------- formatting
def dmy(d):
    return '%d %s %d' % (d.day, MONTHS[d.month - 1], d.year)


def dm(d):
    return '%d %s' % (d.day, MONTHS[d.month - 1])


def span(a, b):
    if a == b:
        return dmy(a)
    if (a.year, a.month) == (b.year, b.month):
        return '%d to %s' % (a.day, dmy(b))
    if a.year == b.year:
        return '%s to %s' % (dm(a), dmy(b))
    return '%s to %s' % (dmy(a), dmy(b))


def signed(v, nd=3):
    s = ('%.' + str(nd) + 'f') % abs(v)
    return ('+' if v > 0 else '−' if v < 0 else '') + s


def dash(s):
    return s.replace('-', '–') if s else s


def week_date(w):
    y, n = w.split('-W')
    return dt.date.fromisocalendar(int(y), int(n), 1)


def week_name(d):
    y, n, _ = d.isocalendar()
    return '%d-W%02d' % (y, n)


def wnum(w):
    return str(int(w.split('-W')[1]))


def load(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def fail(msg):
    raise SystemExit('QuantumPulse front: ' + msg)


# ---------------------------------------------------------------- records
def git(root, *a):
    return subprocess.run(['git', '-C', root, *a], capture_output=True, text=True, check=True).stdout


def history(root, agent_ids):
    rows = []
    for line in git(root, 'log', '--format=%H|%cI|%s').strip().splitlines():
        h, when, subj = line.split('|', 2)
        m = re.search(r'\s*\(#(\d+)\)$', subj)
        t = dt.datetime.fromisoformat(when).astimezone(dt.timezone.utc)
        if m:
            body = subj[:m.start()]
            pre = body.split(':')[0]
            who = body.split(' ')[1] if pre == 'predictions' and ' ' in body else pre
            rows.append({'h': h[:7], 't': t, 'pr': int(m.group(1)), 'title': body, 'pre': pre,
                         'who': who, 'agent': pre in agent_ids or pre in ('predictions', 'log')})
        else:
            rows.append({'h': h[:7], 't': t, 'pr': None, 'title': subj, 'pre': '', 'who': '', 'agent': False})
    if not rows:
        fail('empty git log')
    return rows


def scorer(root):
    spec = importlib.util.spec_from_file_location('qp_evaluator', os.path.join(root, 'company/agents/logic/evaluator.py'))
    ev = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ev)
    sp = ev.score_prediction
    # positive controls: the studio's own function, on answers known in advance
    for pred, act, want in (('2-1', (2, 1), 3), ('1-0', (2, 1), 1), ('0-0', (2, 1), 0), ('1-1', (0, 0), 1), ('x', (1, 1), 0)):
        if sp(pred, act) != want:
            fail('score_prediction(%r, %r) is %r, expected %r' % (pred, act, sp(pred, act), want))
    return sp


def studio(root):
    D = os.path.join(root, 'company/data')
    roster = load(os.path.join(root, 'company/roster.json'))
    ids = [r['id'] for r in roster]
    names = {r['id']: r['ad'] for r in roster}
    personas = [r['id'] for r in roster if r.get('logic') == 'predictor']
    if len(personas) != 3:
        fail('expected three predictors, found %r' % personas)
    sp = scorer(root)

    def res_of(track, w):
        p = os.path.join(D, 'results', track, w + '.json')
        return {r['match_id']: (r['home_goals'], r['away_goals']) for r in load(p)} if os.path.exists(p) else {}

    def preds_of(p, track, w):
        f = os.path.join(D, 'predictions', p, track, w + '.json')
        return load(f) if os.path.exists(f) else None

    def fix_of(track, w):
        f = os.path.join(D, 'fixtures', track, w + '.json')
        return load(f) if os.path.exists(f) else []

    scored = sorted(os.path.basename(f)[:-5] for f in glob.glob(os.path.join(D, 'scores/domestic/*.json'))
                    if re.fullmatch(r'\d{4}-W\d{2}\.json', os.path.basename(f)))
    if not scored:
        fail('no scored week')
    league = load(os.path.join(D, 'league.json'))['tracks']['domestic']['personas']

    tot = {p: {'points': 0, 'exact': 0, 'hits': 0, 'n': 0} for p in personas + ['ghost']}
    by_week = {}
    diffs = []
    for w in scored:
        res = res_of('domestic', w)
        row = {}
        ids_all = set()
        pm = {}
        for p in personas:
            pr = [t for t in (preds_of(p, 'domestic', w) or []) if t['match_id'] in res]
            pts = [sp(t['score'], res[t['match_id']]) for t in pr]
            row[p] = sum(pts)
            ids_all |= {t['match_id'] for t in pr}
            pm[p] = {t['match_id']: t['score'] for t in pr}
            tot[p]['points'] += sum(pts); tot[p]['exact'] += sum(1 for x in pts if x == 3)
            tot[p]['hits'] += sum(1 for x in pts if x >= 1); tot[p]['n'] += len(pts)
        gp = [sp(GHOST, res[i]) for i in ids_all]
        row['ghost'] = sum(gp)
        tot['ghost']['points'] += sum(gp); tot['ghost']['exact'] += sum(1 for x in gp if x == 3)
        tot['ghost']['hits'] += sum(1 for x in gp if x >= 1); tot['ghost']['n'] += len(gp)
        # the week's own score file says the same
        sf = load(os.path.join(D, 'scores/domestic', w + '.json'))
        for p in personas:
            if p in sf and sf[p].get('points') != row[p]:
                fail('%s %s: recomputed %d, score file %r' % (w, p, row[p], sf[p].get('points')))
        for m in res:
            if all(m in pm[p] for p in personas):
                diffs.append(st.mean(sp(pm[p][m], res[m]) for p in personas) - sp(GHOST, res[m]))
        by_week[w] = row
    for p in personas:
        L = league[p]
        if (tot[p]['points'], tot[p]['exact'], tot[p]['hits'] - tot[p]['exact']) != (L['points'], L['exact'], L['outcome']):
            fail('official table not reproduced for %s: %r vs %r' % (p, tot[p], L))

    rnd = random.Random(20261013)
    B = 20000
    boots = sorted(st.mean(rnd.choices(diffs, k=len(diffs))) for _ in range(B))
    gap = {'n': len(diffs), 'mean': st.mean(diffs), 'lo': boots[int(0.025 * B)], 'hi': boots[int(0.975 * B)]}

    # calendar: from the week before the first scored week to the last scored week
    start = week_date(scored[0]) - dt.timedelta(days=7)
    end = week_date(scored[-1])
    weeks = []
    d = start
    while d <= end:
        weeks.append(week_name(d)); d += dt.timedelta(days=7)
    kinds = []
    for i, w in enumerate(weeks):
        if i == 0:
            kinds.append('start')
        elif w in by_week:
            kinds.append('scored')
        elif res_of('domestic', w) and any(preds_of(p, 'domestic', w) for p in personas):
            kinds.append('unscored')
        else:
            kinds.append('none')
    cum = {p: [] for p in personas + ['ghost']}
    for i, w in enumerate(weeks):
        for p in cum:
            prev = cum[p][-1] if cum[p] else 0
            cum[p].append(prev + (by_week[w][p] if w in by_week else 0))
    return {'roster': roster, 'ids': ids, 'names': names, 'personas': personas, 'sp': sp, 'scored': scored,
            'by_week': by_week, 'tot': tot, 'gap': gap, 'weeks': weeks, 'kinds': kinds, 'cum': cum,
            'res_of': res_of, 'preds_of': preds_of, 'fix_of': fix_of, 'D': D}


# ---------------------------------------------------------------- pieces
def first(S, p):
    return S['names'][p].split(' ')[0]


def standings(S, upto=None):
    """Official table rows, ghost first, then predictors by points."""
    if upto is None:
        tot = S['tot']
    else:
        tot = {p: {'points': 0, 'exact': 0, 'hits': 0, 'n': 0} for p in S['personas'] + ['ghost']}
        sp = S['sp']
        for w in S['scored']:
            if w > upto:
                break
            res = S['res_of']('domestic', w)
            ids_all = set()
            for p in S['personas']:
                pr = [t for t in (S['preds_of'](p, 'domestic', w) or []) if t['match_id'] in res]
                pts = [sp(t['score'], res[t['match_id']]) for t in pr]
                ids_all |= {t['match_id'] for t in pr}
                tot[p]['points'] += sum(pts); tot[p]['exact'] += sum(1 for x in pts if x == 3)
                tot[p]['hits'] += sum(1 for x in pts if x >= 1); tot[p]['n'] += len(pts)
            gp = [sp(GHOST, res[i]) for i in ids_all]
            tot['ghost']['points'] += sum(gp); tot['ghost']['exact'] += sum(1 for x in gp if x == 3)
            tot['ghost']['hits'] += sum(1 for x in gp if x >= 1); tot['ghost']['n'] += len(gp)

    def row(k, name, sub):
        t = tot[k]
        n = t['n'] or 1
        return {'k': k, 'name': name, 'sub': sub, 'pts': str(t['points']), 'ppm': '%.3f' % (t['points'] / n),
                'exact': str(t['exact']), 'right': '%.1f%%' % (100 * t['hits'] / n), 'points': t['points'],
                'cls': 'gh' if k == 'ghost' else '', 'rowcls': 'ghost' if k == 'ghost' else ''}
    rows = [row('ghost', 'Home 2–1 (ghost)', 'the home side wins 2–1, every match')]
    pr = sorted(S['personas'], key=lambda p: (-tot[p]['points'], S['names'][p]))
    rows += [row(p, S['names'][p], TEMPER.get(p, p)) for p in pr]
    return rows, tot


def gates(S):
    n = S['tot']['ghost']['n']
    ppm = {p: S['tot'][p]['points'] / max(1, S['tot'][p]['n']) for p in S['personas'] + ['ghost']}
    studio_ppm = st.mean(ppm[p] for p in S['personas'])
    above = sum(1 for p in S['personas'] if S['tot'][p]['points'] > S['tot']['ghost']['points'])
    missing = [w for w, k in zip(S['weeks'], S['kinds']) if k == 'unscored']
    g1 = n >= WINDOW
    g2 = studio_ppm > ppm['ghost'] and S['gap']['lo'] > 0
    g3 = above >= 2
    g4 = not missing
    st_ = lambda o: ('open', 'Open') if o else ('', 'Closed')
    out = [
        {'name': 'Long enough', 'pre': '', 'num': str(n), 'post': ' of %d matches' % WINDOW, 'off': round(max(0, 1 - n / WINDOW), 3), 'open': g1},
        {'name': 'The studio is ahead', 'pre': '', 'num': '%.3f' % studio_ppm, 'post': ' points a match, ghost %.3f' % ppm['ghost'], 'off': 0 if g2 else 1, 'open': g2},
        {'name': 'Most predictors are ahead', 'pre': '', 'num': str(above), 'post': ' of 3 ahead, 2 needed', 'off': 0 if g3 else 1, 'open': g3},
        {'name': 'A complete record', 'pre': '', 'num': '', 'post': 'Every week scored' if g4 else 'Every week scored. Missing: week ' + ', '.join(wnum(w) for w in missing) + '.',
         'off': 0 if g4 else 1, 'open': g4},
    ]
    for g in out:
        g['cls'], g['state'] = st_(g['open'])
    return out, {'n': n, 'studio_ppm': studio_ppm, 'ghost_ppm': ppm['ghost'], 'above': above, 'missing': missing,
                 'all_open': g1 and g2 and g3 and g4}


def led_sentence(S):
    """Which scored weeks a predictor was ahead of the ghost after."""
    led = []
    for i, (w, k) in enumerate(zip(S['weeks'], S['kinds'])):
        if k != 'scored':
            continue
        best = max(S['cum'][p][i] for p in S['personas'])
        led.append(best > S['cum']['ghost'][i])
    m = len(led)
    if not any(led):
        return 'No predictor has been ahead of the ghost after any scored week.'
    if all(led):
        return 'A predictor has been ahead after every scored week.'
    k = 0
    while k < m and led[k]:
        k += 1
    if k and not any(led[k:]):
        return 'The predictors led for the first %s %s.' % (NUMW[k] if k < len(NUMW) else k, 'week' if k == 1 else 'weeks')
    return 'A predictor was ahead of the ghost after %d of %d scored weeks.' % (sum(led), m)


def verdict(S, G):
    n, gap = G['n'], S['gap']
    lead = abs(gap['mean'])
    if G['all_open']:
        return ('Our predictors beat the best you can do without thinking.',
                'Over %d matches the studio averaged %.3f points a match against the ghost’s %.3f.' % (n, G['studio_ppm'], G['ghost_ppm']))
    if gap['mean'] < 0:
        if gap['hi'] < 0:
            return ('The ghost is ahead.',
                    'After %d matches the ghost leads by %.3f points a match, and the whole 95%% interval is below zero. %s' % (n, lead, led_sentence(S)))
        return ('The ghost is ahead. Not by enough to call it.',
                'After %d matches the ghost leads by %.3f points a match, and the uncertainty is wider than the lead. %s' % (n, lead, led_sentence(S)))
    if gap['lo'] <= 0:
        return ('The predictors are ahead. Not by enough to call it.',
                'After %d matches the studio leads the ghost by %.3f points a match, and the uncertainty is wider than the lead.' % (n, lead))
    wait = []
    if n < WINDOW:
        wait.append('%d matches' % WINDOW)
    if G['above'] < 2:
        wait.append('two predictors ahead')
    if G['missing']:
        wait.append('a complete record')
    return ('The predictors are ahead. The claim waits for its gates.',
            'After %d matches the studio leads the ghost by %.3f points a match, and the interval is above zero. Still to come: %s.' % (n, lead, ' and '.join(wait)))


def chart(S):
    """Cumulative points by calendar week, scaled for any number of weeks."""
    W, K, cum = S['weeks'], S['kinds'], S['cum']
    N = len(W)
    top = max(max(v) for v in cum.values())
    step = 50 if top <= 300 else 100 if top <= 600 else 250
    ymax = max(step, -(-top // step) * step)
    ticks = list(range(0, ymax + 1, step))
    xs = [70 + i * 730 / max(1, N - 1) for i in range(N)]
    unit = 730 / max(1, N - 1)
    bands = []
    i = 1
    while i < N:
        if K[i] in ('unscored', 'none'):
            j = i
            while j + 1 < N and K[j + 1] == K[i]:
                j += 1
            left = xs[i - 1]
            bands.append({'k': K[i], 'left': round(left / 10, 3), 'width': round((xs[j] - xs[i - 1]) / 10, 3),
                          'mid': round((xs[i - 1] + xs[j]) / 2 / 10, 2),
                          'label': 'Not scored' if K[i] == 'unscored' else 'No matches',
                          'cls': 'hband hband-x' if K[i] == 'unscored' else 'hband'})
            i = j + 1
        else:
            i += 1
    scored_idx = [0] + [i for i, k in enumerate(K) if k == 'scored']
    # lead changes at scored weeks
    lcs, leader_at, prev = [], {}, None
    for i in scored_idx[1:]:
        vals = {p: cum[p][i] for p in S['personas'] + ['ghost']}
        best = max(vals.values())
        lead = tuple(sorted(p for p, v in vals.items() if v == best))
        leader_at[i] = lead
        if lead != prev:
            lcs.append({'i': i, 'v': best, 'lead': lead})
        prev = lead
    last = lcs[-1] if lcs else None
    note = ''
    if last and len(lcs) > 1:
        who = ' and '.join('Ghost' if p == 'ghost' else first(S, p) for p in last['lead'])
        note = '%s %s from week %s' % (who, 'lead' if len(last['lead']) > 1 else 'leads', wnum(W[last['i']]))
    return {'weeks': [wnum(w) for w in W], 'kinds': K, 'scored_idx': scored_idx, 'ymax': ymax, 'ticks': ticks,
            'bands': bands, 'lcs': [{'i': c['i'], 'v': c['v']} for c in lcs],
            'note': note, 'note_i': last['i'] if last else 0, 'note_v': last['v'] if last else 0,
            'cum': cum, 'first': wnum(W[1]) if N > 1 else wnum(W[0]), 'last': wnum(W[-1])}


def kickoff(iso):
    t = dt.datetime.fromisoformat(iso.replace('Z', '+00:00')).astimezone(dt.timezone.utc)
    return t, '%s %d %s, %02d:%02d UTC' % (WDAY[t.weekday()], t.day, MONTHS[t.month - 1], t.hour, t.minute)


def week_card(S, w, track='domestic'):
    """One week: every fixture, the three scorelines, the ghost, the result, the points."""
    sp = S['sp']
    fixtures = S['fix_of'](track, w)
    res = S['res_of'](track, w)
    preds = {p: {t['match_id']: t for t in (S['preds_of'](p, track, w) or [])} for p in S['personas']}
    predicted = set().union(*[set(v) for v in preds.values()])
    official = track == 'domestic' and w in S['by_week']
    europe_scored = track == 'europe' and os.path.exists(os.path.join(S['D'], 'scores/europe', w + '.json'))
    scored = official or europe_scored
    byid = {f['match_id']: f for f in fixtures}
    for mid in predicted:          # a prediction for a match missing from the fixture file still shows
        if mid not in byid:
            t = next(preds[p][mid] for p in S['personas'] if mid in preds[p])
            byid[mid] = {'match_id': mid, 'league': '?', 'home': t['home'], 'away': t['away'], 'date': None}
    codes = [EUROPE] if track == 'europe' else LEAGUES
    leagues = []
    dates = []
    totals = {p: 0 for p in S['personas'] + ['ghost']}
    for code, lname in codes:
        ms = [f for f in byid.values() if (f.get('league') == code or track == 'europe') and f['match_id'] in predicted]
        ms.sort(key=lambda f: (f.get('date') or '', f['home']))
        rows = []
        for f in ms:
            m = {'id': f['match_id'], 'home': f['home'], 'away': f['away'], 'p': {}}
            if f.get('date'):
                t, m['when'] = kickoff(f['date'])
                m['date'] = f['date']
                dates.append(t.date())
            else:
                m['when'] = ''
                m['date'] = ''
            r = res.get(f['match_id'])
            m['result'] = '%d-%d' % r if r else ''
            for p in S['personas']:
                t = preds[p].get(f['match_id'])
                why = (t.get('reasoning') or '') if t else ''
                if BANNED.search(why):
                    why = 'Reason not shown: it uses betting vocabulary, which this site does not print.'
                e = {'s': t['score'] if t else '', 'why': why}
                if r and scored and t:
                    e['pts'] = sp(t['score'], r)
                    totals[p] += e['pts']
                m['p'][p] = e
            if r and scored:
                m['final'] = m['result']
                m['ghost'] = sp(GHOST, r)
                totals['ghost'] += m['ghost']
            m['state'] = 'scored' if (r and scored) else ('unscored' if r else 'pending')
            rows.append(m)
        if rows:
            leagues.append({'code': code, 'name': lname, 'matches': rows})
    if not leagues:
        return None
    period = span(min(dates), max(dates)) if dates else ''
    n = sum(len(L['matches']) for L in leagues)
    nres = sum(1 for L in leagues for m in L['matches'] if m['result'])
    if scored:
        state = 'scored'
    elif nres:
        state = 'unscored'
    else:
        state = 'pending'
    return {'week': w, 'num': wnum(w), 'track': track, 'period': period, 'leagues': leagues, 'n': n, 'nres': nres,
            'state': state, 'official': official, 'tot': {k: v for k, v in totals.items()} if scored else None}


def pending_text(card):
    if card['state'] == 'pending':
        return 'No result yet.'
    if card['state'] == 'unscored':
        return 'No result recorded. Not scored.'
    return 'No result recorded. Not scored.'


def week_line(S, card):
    lead = 'Week %s, all five leagues' % card['num']
    if card['state'] == 'scored':
        t = card['tot']
        order = sorted(S['personas'], key=lambda p: (-t[p], first(S, p)))
        return '%s: %s. Ghost, home 2–1: %d.' % (lead, ', '.join('%s %d' % (first(S, p), t[p]) for p in order), t['ghost'])
    if card['state'] == 'unscored':
        return '%s: the results are in; the week has not been scored yet.' % lead
    return '%s: no results yet. The week is scored after the weekend.' % lead


def excerpt(text, limit=300):
    lines = [l.strip() for l in text.splitlines()]
    body = ' '.join(l for l in lines if l and not l.startswith(('#', '- ', '* ', '|')) and not re.fullmatch(r'[A-Z][\w .’\'-]+, [A-Z][\w ,:’\'-]+', l))
    sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+', body) if s.strip()]
    sents = [s for s in sents if not BANNED.search(s)]
    if not sents:
        return ''
    if len(sents) <= 2:
        out = ' '.join(sents)
    else:
        out = sents[0] + ' … ' + sents[-1]
    if len(out) > limit:
        out = sents[0]
    if len(out) > limit:
        out = out[:limit].rsplit(' ', 1)[0] + ' …'
    return out


def homework(root, S):
    out = []
    mins = os.path.join(root, 'company/minutes')
    for who, pat, cap, head in (('pessimist', '*-pessimist.md', 'Minutes, excerpt', 'Minutes'),
                                ('evaluator', '*-evaluator-retro.md', 'Retro, excerpt', 'Retro')):
        files = sorted(glob.glob(os.path.join(mins, pat)))
        if not files:
            continue
        f = files[-1]
        d = dt.date.fromisoformat(os.path.basename(f)[:10])
        text = open(f, encoding='utf-8').read()
        q = excerpt(text)
        if not q:
            continue
        what = head + ', ' + dmy(d)
        if who == 'evaluator':
            m = re.search(r'Retro\s+[—-]\s+(\d{4}-W\d{2})', text)
            if m:
                what = 'Retro for week %s, %s' % (wnum(m.group(1)), dmy(d))
        out.append({'img': 'assets/portraits/quantumpulse/%s.svg' % who,
                    'who': '%s, %s, wrote' % (S['names'][who], 'the critic' if who == 'pessimist' else 'the evaluator'),
                    'what': what, 'cap': cap, 'q': q})
    return out


def hallway(root, S, k=6):
    rows = []
    for f in sorted(glob.glob(os.path.join(root, 'company/hallway/*.txt'))):
        m = re.match(r'(\d{4}-\d{2}-\d{2})-([a-z]+)\.txt$', os.path.basename(f))
        if not m or m.group(2) not in S['names']:
            continue
        t = open(f, encoding='utf-8').read().strip()
        name = S['names'][m.group(2)]
        if t.startswith(name + ':'):
            t = t[len(name) + 1:].strip()
        if not t or BANNED.search(t):
            continue
        rows.append({'d': m.group(1), 'id': m.group(2), 'name': name, 't': t})
    rows = rows[-k:]
    return [{'img': 'assets/portraits/quantumpulse/%s.svg' % r['id'], 'name': r['name'],
             'date': dmy(dt.date.fromisoformat(r['d'])), 'q': r['t']} for r in rows]


# ---------------------------------------------------------------- templates
def tpl(root, name):
    return open(os.path.join(root, 'front', 'pages', name.replace('.html', '.dc.html')), encoding='utf-8').read()


def nav(current):
    items = []
    for href, label in NAV:
        cur = ' aria-current="page"' if href == current else ''
        items.append('<li><a href="%s"%s>%s</a></li>' % (href, cur, label))
    return '<ul class="nav">\n' + '\n'.join(items) + '\n</ul>'


def build(root):
    S = studio(root)
    roster = S['roster']
    hist = history(root, S['ids'])
    agent_prs = [h for h in hist if h['pr'] is not None and h['agent']]
    merges = [h for h in hist if h['pr'] is not None]
    ops = [h for h in hist if h['pr'] is None]
    if not merges:
        fail('no merged change in the log')
    last = merges[0]
    asof = last['t'].date()
    asof_s = dmy(asof)
    day = (asof - DAY_ONE).days + 1
    status = {'text': 'Running. Day %d.' % day, 'date': asof_s, 'cls': '',
              'title': 'Day 1 was %s. A change merged in the last %d hours, so the light is on.' % (dmy(DAY_ONE), QUIET_HOURS),
              'last_merge_utc': last['t'].strftime('%Y-%m-%dT%H:%M:%SZ'), 'quiet_hours': QUIET_HOURS}
    on_leave = {r['id']: LEAVE.get(r['id'], '') for r in roster if not r.get('gunler')}
    on_duty = len(roster) - len(on_leave)
    revision = str(len(agent_prs))
    folio_n = {n: i + 1 for i, n in enumerate(ORDER)}

    rows, tot = standings(S)
    G, gs = gates(S)
    head, body = verdict(S, gs)
    ch = chart(S)
    gap = S['gap']

    # weeks with predictions, newest first (domestic and Champions League nights)
    pw = set()
    for p in S['personas']:
        for tr in ('domestic', 'europe'):
            for f in glob.glob(os.path.join(S['D'], 'predictions', p, tr, '*.json')):
                pw.add((os.path.basename(f)[:-5], tr))
    cards = {}
    for w, tr in sorted(pw):
        c = week_card(S, w, tr)
        if c:
            cards.setdefault(w, []).append(c)
    latest_w = max(w for w, tr in pw if tr == 'domestic')
    latest = next(c for c in cards[latest_w] if c['track'] == 'domestic')

    best = max(tot[p]['points'] for p in S['personas'])
    ghost_pts = tot['ghost']['points']
    if gs['all_open']:
        tail = 'The gates are open, so the claim is on.'
    elif best >= ghost_pts:
        tail = 'The claim still waits for its gates; it switches on by itself, and not a day before.'
    else:
        tail = 'We publish it anyway. When the record turns, the claim switches on by itself, and not a day before.'
    under = {'best': best, 'ghost': ghost_pts, 'tail': tail}

    missing_note = []
    unscored = [w for w, k in zip(S['weeks'], S['kinds']) if k == 'unscored']
    nomatch = [w for w, k in zip(S['weeks'], S['kinds']) if k == 'none' and w != S['weeks'][0]]
    def wl(ws):
        ns = [wnum(w) for w in ws]
        return ns[0] if len(ns) == 1 else ', '.join(ns[:-1]) + ' and ' + ns[-1]
    if nomatch:
        missing_note.append('%s %s had no matches.' % ('Week' if len(nomatch) == 1 else 'Weeks', wl(nomatch)))
    if unscored:
        missing_note.append('%s %s %s never scored because of a timing fault; %s left out for everyone.' % (
            'Week' if len(unscored) == 1 else 'Weeks', wl(unscored), 'was' if len(unscored) == 1 else 'were',
            'it’s' if len(unscored) == 1 else 'they’re'))
    note = ' '.join(missing_note)

    # the interval drawing: a range that holds the interval and zero, in tenths
    lo_v = min(gap['lo'], 0) - 0.05
    hi_v = max(gap['hi'], 0) + 0.05
    lo_t, hi_t = math.floor(lo_v * 10) / 10, math.ceil(hi_v * 10) / 10
    X = lambda v: 80 + (v - lo_t) / (hi_t - lo_t) * 840
    ivt = []
    t = lo_t
    while t <= hi_t + 1e-9:
        ivt.append({'x': round(X(t) / 10, 2), 't': ('0' if abs(t) < 1e-9 else signed(t, 1)), 'cls': 'vl' if abs(t) < 1e-9 else 'tl', 'sx': round(X(t), 1)})
        t = round(t + 0.1, 10)
    iv = {'ticks': ivt, 'x0': round(X(0), 1), 'xlo': round(X(gap['lo']), 1), 'xhi': round(X(gap['hi']), 1),
          'plo': round(X(gap['lo']) / 10, 2), 'pm': round(X(gap['mean']) / 10, 2), 'phi': round(X(gap['hi']) / 10, 2),
          'lo': signed(gap['lo']), 'mean': signed(gap['mean']), 'hi': signed(gap['hi']),
          'ghostL': round((80 + X(0)) / 2 / 10, 2), 'studioL': round((X(0) + 920) / 2 / 10, 2),
          'aria': 'The studio scores %.3f points a match %s than the ghost. The 95%% interval runs from %s %.3f to %s %.3f, so it %s zero.' % (
              abs(gap['mean']), 'fewer' if gap['mean'] < 0 else 'more', 'minus' if gap['lo'] < 0 else 'plus', abs(gap['lo']),
              'minus' if gap['hi'] < 0 else 'plus', abs(gap['hi']), 'includes' if gap['lo'] <= 0 <= gap['hi'] else 'excludes')}

    # roster for the week dial and the floor plan
    crew = []
    for r in roster:
        days = sorted(GUNLER[g] for g in r.get('gunler') or [])
        crew.append({'k': r['id'], 'name': r['ad'].split(' ')[0], 'full': r['ad'], 'img': 'assets/portraits/quantumpulse/%s.svg' % r['id'],
                     'days': days, 'leave': r['id'] in on_leave,
                     'title': '%s, %s. %s' % (r['ad'], ROLE.get(r['id'], r['rol']),
                                              ('On leave since %s.' % dmy(dt.date.fromisoformat(on_leave[r['id']])) if on_leave.get(r['id'])
                                               else 'On leave.') if r['id'] in on_leave else 'On shift: %s.' % ', '.join(WDAY[d] for d in days))})
    last_day = [h for h in agent_prs if h['t'].date() == last['t'].date()][:3]
    marks = [{'who': h['who'], 'when': '%02d:%02d UTC, %s' % (h['t'].hour, h['t'].minute, dmy(h['t'].date())), 'title': h['title']} for h in reversed(last_day)]

    teaser = {'url': '/agent-capital/summary.json', 'headline': '', 'asof': ''}
    common = {'status': status, 'next': teaser}
    leave_names = [S['names'][k] for k in on_leave]

    pages = []
    def add(name, live):
        live = dict(common, **live)
        fol = {'Sheet': SHEET[name], 'Number': 'Sheet %d of %d' % (folio_n[name], len(ORDER)), 'Revision': revision,
               'Drawn by': '%d agents' % on_duty, 'As of': asof_s}
        pages.append({'out': name, 'tpl': tpl(root, name), 'desc': DESC[name], 'folio': fol, 'live': live})

    race = {'head': head, 'body': body, 'under': under, 'note': note, 'asof': 'As of ' + asof_s,
            'rows': rows, 'caption': 'Official table, %d matches, weeks %s to %s' % (gs['n'], ch['first'], ch['last'])}
    ppl = [[p, first(S, p)] for p in S['personas']]
    add('index.html', {'race': race, 'chart': ch, 'pred': ppl, 'card': latest,
                       'cardAsof': 'Week %s, %s' % (latest['num'], latest['period']),
                       'cardLabel': 'Week %s card, %d fixtures' % (latest['num'], latest['n']),
                       'weekLine': week_line(S, latest), 'na': pending_text(latest),
                       'crew': crew, 'marks': marks,
                       'marksLabel': 'A change merging, %s' % dmy(last['t'].date()),
                       'homework': homework(root, S), 'hall': hallway(root, S), 'asofDate': asof_s})
    add('proof.html', {'race': race, 'chart': ch, 'pred': ppl, 'gates': G, 'iv': iv,
                       'holds': {'asof': 'As of ' + asof_s,
                                 'merged': '%d changes made by agents have merged. Human approvals: 0.' % len(agent_prs)}})
    # Matches: every week, every prediction
    wk_list = []
    for w in sorted(cards, reverse=True):
        for c in sorted(cards[w], key=lambda c: c['track'] != 'domestic'):
            ups = max([s for s in S['scored'] if s <= w], default=None)
            srows = standings(S, upto=ups)[0] if ups else []
            c = dict(c)
            c['label'] = ('Week %s' % c['num']) + (', Champions League' if c['track'] == 'europe' else '')
            c['note'] = {'scored': 'Scored.' if c['official'] else 'Scored, but not part of the official table, which counts the five domestic leagues.',
                         'unscored': 'Results recorded, never scored (a timing fault). Not in the table.' if c['week'] < S['scored'][-1] or c['week'] in unscored
                                     else 'Results recorded, not scored yet.',
                         'pending': 'No results yet. The week is scored after the weekend.'}[c['state']]
            if c['track'] == 'europe':
                c['note'] = 'Champions League night. ' + ('Scored separately; not part of the official table, which counts the five domestic leagues.' if c['state'] == 'scored' else c['note'])
            c['table'] = srows if ups else []
            c['tableCap'] = ('Official table after week %s' % wnum(ups)) if ups else ''
            wk_list.append(c)
    add('matches.html', {'weeks': wk_list, 'pred': ppl, 'asof': 'As of ' + asof_s})
    belt = [[h['title'], '#%d, %s' % (h['pr'], dm(h['t'].date()))] for h in reversed(agent_prs[:12])]
    add('how-it-runs.html', {'belt': belt,
                             'beltCap': 'Red cards are examples of what gets sent back: a test failed, the change touches the locked core, or betting language was found. Every other card is a real change from %s, stamped as it merged.' % span(agent_prs[11]['t'].date() if len(agent_prs) > 11 else agent_prs[-1]['t'].date(), agent_prs[0]['t'].date()),
                             'ops': 'Renews the keys and occasionally repairs the plumbing, in public. Doesn’t decide what the firms predict, trade, write or design. Maintenance commits from %s: %d.' % (
                                 span(DAY_ONE, ops[0]['t'].date()), len(ops)),
                             'staffLine': '%s agents with names, jobs, schedules and faces%s The box at the top of the chart is empty on purpose.' % (
                                 NUMW[len(roster)].capitalize() if len(roster) < len(NUMW) else str(len(roster)),
                                 ('. %s %s on leave.' % (' and '.join(leave_names), 'is' if len(leave_names) == 1 else 'are')) if leave_names else '.'),
                             'leave': {k: True for k in on_leave}})
    # staff and log: the shared generator when it is there, else the frozen pages
    ctx = {'leave': on_leave, 'status': status, 'asof': asof_s, 'as_of': asof_s, 'as_of_iso': asof.isoformat(), 'revision': revision, 'on_duty': on_duty, 'next': teaser}
    gen = None
    sl = os.path.join(root, 'front', 'staff_log.py')
    if os.path.exists(sl):
        spec = importlib.util.spec_from_file_location('staff_log', sl)
        gen = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gen)
    made = gen.build(root, 'QP', ctx) if gen else {}
    for name in ('staff.html', 'log.html'):
        live = dict(common)
        if name in made:
            t = made[name]
        else:
            t = tpl(root, name)
        fol = {'Sheet': SHEET[name], 'Number': 'Sheet %d of %d' % (folio_n[name], len(ORDER)), 'Revision': revision,
               'Drawn by': '%d agents' % on_duty, 'As of': asof_s}
        pages.append({'out': name, 'tpl': t, 'desc': DESC[name], 'folio': fol, 'live': live})
    pages.sort(key=lambda p: ORDER.index(p['out']))

    summary = {'headline': '%d matches scored' % gs['n'], 'asof': 'As of ' + asof_s, 'ghost': 'Ghost: Home 2–1'}
    redirects = {'predictions.html': 'matches.html', 'office.html': 'staff.html', 'changelog.html': 'log.html',
                 'index.html': '', '': ''}
    return {'nav': nav, 'redirects': redirects, 'pages': pages, 'summary': summary}
