#!/usr/bin/env python3
"""Refresh this repo from the VeritaHire Job Openings Index, published daily at
https://veritahire.com/job-openings-index/ (computed each morning about 08:25 UTC).

Writes:
  data/job-openings-index.csv   the daily series (VeritaHire's own columns)
  data/latest.json              today's headline numbers
  chart.svg                     the index and its 7-day average since the base date
  README.md                     the block between <!-- latest:start --> and <!-- latest:end -->

Standard library only, so the GitHub Action needs no installs.
"""
import csv, io, json, os, sys, urllib.request
from datetime import date

SRC = 'https://veritahire.com/job-openings-index/'
UA = {'User-Agent': 'us-job-openings-index-updater (+https://github.com/veritahire/us-job-openings-index)'}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEEP = ['date', 'index', 'index_7d_avg', 'first_published', 'panel_employers', 'open_postings_in_panel',
        'weekly_posting_rate', 'weekly_closing_rate', 'employers_excluded_board_event']
LATEST_KEYS = ['name', 'base', 'base_value', 'data_through', 'computed_at', 'index', 'index_7d_avg',
               'change_1d_pct', 'change_7d_pct', 'change_28d_pct', 'change_since_base_pct',
               'panel_employers', 'open_postings_in_panel', 'weekly_posting_rate', 'weekly_closing_rate', 'method']


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read().decode('utf-8')


def chart(rows):
    """A small, dependency-free SVG line chart of index and index_7d_avg."""
    pts = [(r['date'], float(r['index']), float(r['index_7d_avg'])) for r in rows if r.get('index')]
    if len(pts) < 2:
        return ''
    W, H, L, R, T, B = 880, 320, 56, 20, 30, 46
    lo = min(min(p[1], p[2]) for p in pts + [('', 100.0, 100.0)])
    hi = max(max(p[1], p[2]) for p in pts + [('', 100.0, 100.0)])
    pad = max(0.5, (hi - lo) * 0.15)
    lo, hi = lo - pad, hi + pad
    x = lambda i: L + (W - L - R) * i / (len(pts) - 1)
    y = lambda v: T + (H - T - B) * (hi - v) / (hi - lo)
    line = lambda k: ' '.join(f'{x(i):.1f},{y(p[k]):.1f}' for i, p in enumerate(pts))
    ticks = []
    step = (hi - lo) / 4
    for j in range(5):
        v = lo + step * j
        ticks.append(f'<line x1="{L}" x2="{W - R}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="#e5e7eb"/>'
                     f'<text x="{L - 8}" y="{y(v) + 4:.1f}" text-anchor="end" font-size="11" fill="#6b7280">{v:.1f}</text>')
    labels = []
    for i in sorted({0, len(pts) // 2, len(pts) - 1}):
        d = date.fromisoformat(pts[i][0])
        labels.append(f'<text x="{x(i):.1f}" y="{H - B + 18}" text-anchor="middle" font-size="11" fill="#6b7280">'
                      f'{d.strftime("%b")} {d.day}, {d.year}</text>')
    last = pts[-1]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Helvetica, Arial, sans-serif">
<rect width="{W}" height="{H}" fill="#ffffff"/>
<text x="{L}" y="18" font-size="13" font-weight="700" fill="#111827">VeritaHire Job Openings Index ({pts[0][0]} = 100)</text>
{''.join(ticks)}
<line x1="{L}" x2="{W - R}" y1="{y(100):.1f}" y2="{y(100):.1f}" stroke="#9ca3af" stroke-dasharray="4 4"/>
<polyline points="{line(1)}" fill="none" stroke="#93c5fd" stroke-width="1.5"/>
<polyline points="{line(2)}" fill="none" stroke="#0b7a47" stroke-width="2.5"/>
<circle cx="{x(len(pts) - 1):.1f}" cy="{y(last[2]):.1f}" r="3.5" fill="#0b7a47"/>
<text x="{W - R}" y="18" text-anchor="end" font-size="11" fill="#0b7a47">7-day average {last[2]:.2f}</text>
<text x="{W - R - 130}" y="18" text-anchor="end" font-size="11" fill="#3b82f6">daily {last[1]:.2f}</text>
{''.join(labels)}
<text x="{L}" y="{H - 6}" font-size="10" fill="#9ca3af">Source: VeritaHire, veritahire.com/job-openings-index</text>
</svg>
'''


def readme_block(latest):
    sign = lambda v: ('+' if v is not None and v > 0 else '') + (f'{v:.2f}%' if v is not None else 'n/a')
    return (f"**{latest['index_7d_avg']:.2f}** (7-day average, {latest['base']} = 100), data through "
            f"**{latest['data_through']}**, published {latest['computed_at'].replace('T', ' ')}.\n\n"
            f"| | |\n|---|---|\n"
            f"| Daily index | {latest['index']:.2f} |\n"
            f"| Change, 1 day | {sign(latest.get('change_1d_pct'))} |\n"
            f"| Change, 7 days | {sign(latest.get('change_7d_pct'))} |\n"
            f"| Change, 28 days | {sign(latest.get('change_28d_pct'))} |\n"
            f"| Change since {latest['base']} | {sign(latest.get('change_since_base_pct'))} |\n"
            f"| Employers in the panel | {latest['panel_employers']:,} |\n"
            f"| Open postings in the panel | {latest['open_postings_in_panel']:,} |\n"
            f"| New postings this week, share of open | {latest['weekly_posting_rate'] * 100:.1f}% |\n"
            f"| Postings closed this week, share of open | {latest['weekly_closing_rate'] * 100:.1f}% |\n")


def main():
    raw = list(csv.DictReader(io.StringIO(get(SRC + 'veritahire-job-openings-index.csv'))))
    if not raw or 'index' not in raw[0]:
        sys.exit('source CSV missing or changed shape; nothing written')
    rows = [{k: r.get(k, '') for k in KEEP} for r in raw]
    full = json.loads(get(SRC + 'latest.json'))
    latest = {k: full[k] for k in LATEST_KEYS if k in full}
    latest['source'] = SRC

    with open(os.path.join(ROOT, 'data', 'job-openings-index.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=KEEP, lineterminator='\n')
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(ROOT, 'data', 'latest.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(latest, f, indent=1)
        f.write('\n')
    svg = chart(rows)
    if svg:
        with open(os.path.join(ROOT, 'chart.svg'), 'w', encoding='utf-8', newline='\n') as f:
            f.write(svg)

    path = os.path.join(ROOT, 'README.md')
    text = open(path, encoding='utf-8').read()
    a, b = '<!-- latest:start -->', '<!-- latest:end -->'
    if a in text and b in text:
        head, rest = text.split(a, 1)
        tail = rest.split(b, 1)[1]
        text = head + a + '\n' + readme_block(latest) + b + tail
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
    print(f"updated through {latest['data_through']}: index {latest['index']}, 7d {latest['index_7d_avg']}, {len(rows)} days")


if __name__ == '__main__':
    main()
