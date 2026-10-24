"""Render public results only; never publish raw discovery notes or credentials."""
import html
import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
def esc(value):
    return html.escape(str(value))
def link(url, label):
    parsed = urlparse(url)
    if parsed.scheme != 'https' or not parsed.hostname:
        return ''
    return f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer">{esc(label)}</a>'

def main():
    results = []
    for path in sorted((ROOT / 'data').glob('*.json')):
        results.append(json.loads(path.read_text()))
    cards, coverage = [], []
    total = 0
    for result in results:
        coverage.append(f'<h3>{esc(result["institution"])}</h3><p>Checked: {esc(result["checked"])}</p>'
                        f'<p>{esc(result.get("coverage", ""))}</p><p><strong>Gaps:</strong> {esc(result.get("gaps", ""))}</p>')
        for row in result.get('opportunities', []):
            if row.get('record_kind') == 'background':
                continue
            good = row.get('shortlisted') is True
            total += int(good)
            status = 'Shortlisted programme' if good and row['record_kind'] == 'phd_programme' else 'Shortlisted vacancy' if good else 'Unconfirmed / not shortlisted'
            details = ''.join(f'<dt>{esc(label)}</dt><dd>{esc(row.get(key, "not stated"))}</dd>'
                for key, label in [('supervisor','Supervisor'), ('topic','Research'),
                ('funding_amount','Funding'), ('funding_duration','Funding duration'),
                ('tuition_and_fees','Tuition and fees'), ('international_eligibility','International eligibility'),
                ('deadline','Application dates'), ('start_date','Start date'), ('caveats','Important caveats')])
            evidence = ''.join(f'<p><strong>{esc(label)}:</strong> {esc(row.get(key,"not stated"))}</p>'
                for key, label in [('funding_quote','Funding excerpt'),('open_status_quote','Application-status excerpt')])
            search = esc(' '.join(str(v) for v in row.values()) + ' ' + result['institution'])
            cards.append(f'<article data-search="{search.lower()}" data-shortlisted="{str(good).lower()}">'
                f'<p class="badge">{status} · Funding {esc(row["funding_category"])} · {esc(row["open_status"])}</p>'
                f'<h2>{esc(row["title"])}</h2><p>{esc(result["institution"])} · {esc(result["country"])} · Checked {esc(result["checked"])}</p>'
                f'<dl>{details}</dl><p>{link(row["official_url"],"Official programme / advert")} · '
                f'{link(row["funding_url"],"Funding source")} · {link(row.get("open_status_url",""),"Application dates")}</p>'
                f'<details><summary>Show model-collected source excerpts</summary>{evidence}</details></article>')
    page = '''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Evidence-first search for funded cancer biology PhDs in Canada and Europe.">
<title>Cancer PhD Finder</title><style>
body{font:16px/1.6 system-ui,sans-serif;margin:0;background:#f5f7fb;color:#17243a}main{max-width:1000px;margin:auto;padding:32px 20px}
h1{font-size:2.4rem;margin-bottom:0}h2{line-height:1.3}a{color:#1857b5}article,.notice{background:white;border:1px solid #dbe1ea;border-radius:14px;padding:22px;margin:20px 0}
.notice{border-left:5px solid #c38718}.badge{font-weight:700;color:#31536d}dt{font-weight:650}dd{margin:0 0 12px}input[type=search]{padding:12px;width:min(90%,520px);font:inherit;border:1px solid #aab8c8;border-radius:8px}
label{display:block;margin-top:10px}summary{cursor:pointer}footer{margin-top:36px;font-size:.9rem}
</style></head><body><main><h1>Cancer PhD Finder</h1><p>Funded cancer biology and cancer-rooted cell & molecular biology · Canada & Europe</p>
<div class="notice"><strong>Research prototype — not an admissions service.</strong> Results are model-researched leads, not independently certified vacancies.
Check official sources before applying. Programme funding is not a cancer-lab offer. Eligibility has not been tailored to an applicant.
This is a limited pilot, not an exhaustive search. Results are snapshots and may expire.</div>
<p>SUMMARY</p><input id="query" type="search" placeholder="Filter by university, country or cancer topic" aria-label="Filter opportunities">
<label><input id="only" type="checkbox" checked> Show shortlisted results only</label><p id="count" aria-live="polite"></p>
<section>CARDS</section><details><summary>Institutions checked and remaining gaps</summary>COVERAGE</details>
<footer>Funding: A = funded vacancy; B = funded programme; C = conditional funding; D = unclear funding.<br>
Searches are started manually through GitHub Actions by a repository maintainer. This website cannot access model credentials or launch paid searches.
<p><a href="https://github.com/Pbernoos/cancer-phd-finder">Source code, setup and search workflow</a></p></footer></main>
<script>const q=document.getElementById('query'),only=document.getElementById('only');function filter(){let n=0;document.querySelectorAll('article').forEach(el=>{el.hidden=!(el.dataset.search.includes(q.value.toLowerCase())&&(!only.checked||el.dataset.shortlisted==='true'));if(!el.hidden)n++;});document.getElementById('count').textContent=n+' results displayed';}q.addEventListener('input',filter);only.addEventListener('change',filter);filter();</script></body></html>'''
    page = page.replace('SUMMARY', f'{total} shortlisted routes across {len(results)} institution(s) checked. Six institutions are configured as search seeds.')
    page = page.replace('CARDS', '\n'.join(cards)).replace('COVERAGE', '\n'.join(coverage))
    (ROOT / 'docs').mkdir(exist_ok=True)
    (ROOT / 'docs/index.html').write_text(page)
    print(f'Built site: {total} shortlisted routes; {len(results)} institutions checked.')

if __name__ == '__main__':
    main()