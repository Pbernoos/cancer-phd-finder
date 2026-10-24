# Cancer PhD Finder

**[Open the results website](https://pbernoos.github.io/cancer-phd-finder/)**

A working research prototype for finding funded cancer biology PhDs in Canada
and Europe, university by university. Focus: cancer-rooted cell/molecular biology,
tumour genetics/epigenetics, metastasis, cancer immunology and resistance.

## Status

- Public static results website, with searchable cards, evidence links and caveats.
- Manual search workflow only: **no scheduled searches**.
- Six institution seeds: Toronto, McGill, UBC, Oxford, Heidelberg and Karolinska.
- Initial Toronto pilot only. This is not comprehensive geographic coverage.
- Model-based research is not independent verification. Review official sources.
- A funded programme is not a confirmed funded cancer-specific lab vacancy.
- No applications or emails are submitted.

## Run a new search online

The site displays results; searches execute in **GitHub Actions**, not in your
browser. No model credentials are included in this repository.

1. Add your own OpenAI API key as described below in **Settings → Secrets and variables → Actions**.
2. Open **Actions → Search one university (manual) → Run workflow**.
3. Select a university and explicitly authorize the paid model/web-search calls.
4. A successful run updates the public structured results and deploys the website.

Each run makes two model requests (discovery and verification), each capped at
eight web-tool calls. There is no hard dollar-spend cap. The first pass uses
gpt-5.4-mini and the verification pass uses gpt-5.4.

### Model access requirements

The GitHub search workflow explicitly uses your **own OpenAI API account** and
the Responses API with web_search. Create a dedicated project API key at
https://platform.openai.com/api-keys and configure API billing in that account.
A ChatGPT subscription is separate from API billing. Required model/tool access
must be available to that API project. No model calls have been made to test
your account's access or billing.

Create this repository **secret** under **Settings → Secrets and variables → Actions → New repository secret**:

| Name | Value |
| --- | --- |
| `PHD_OPENAI_API_KEY` | Your own OpenAI API key with Responses, model and web_search access |

No W&B variables are needed for the GitHub workflow. The ARIA session credentials
have NOT been exported. The default local runtime remains the project-scoped
W&B proxy; GitHub's explicit `github-openai` runtime only runs in GitHub Actions
and reads only the dedicated `PHD_OPENAI_API_KEY` secret. There is no automatic
provider fallback. Adding a secret does not start a search.

To check setup without paid calls, open **Actions → Check agent configuration (no model calls)**.
This checks code and whether a key is present; it does NOT verify authentication,
model access or billing. Only the manual search workflow makes paid model calls.
Use account spending controls where available; the workflow has no hard dollar cap.

Never put API keys in a public file, a browser script, an issue, or workflow logs.
Use a dedicated limited credential where supported. GitHub Actions workflows run
with the repository's permissions; only trusted maintainers should edit them.

## Run locally

Python 3.10+:

```bash
pip install -r requirements.txt
python cancer_phd_agent.py --self-test
# With the authorized model environment configured:
python cancer_phd_agent.py --institution mcgill --phase discover
python cancer_phd_agent.py --institution mcgill --phase verify --model gpt-5.4
```

Local results are saved in `phd-search/`. Existing discovery is resumable; use a
new `--state` directory for a fresh pass. Add universities and verified affiliate
domains to `INSTITUTIONS` and to the manual workflow's choice list.

Rebuild the website from published records in `data/`:

```bash
python build_site.py
```

## Funding and evidence

- **A**: explicitly funded advertised PhD position.
- **B**: programme guarantees funding to admitted PhD students.
- **C**: conditional/competitive funding, including externally funded applicants.
- **D**: funding unclear.

The shortlist requires official-domain evidence URLs returned by the verification
search, model-confirmed PhD/cancer fit and funding guarantees, and an active call.
Structured past closing dates and future opening dates are rejected. Background
policies, existing-student awards and non-PhD fellowships are not shortlisted.

These checks cannot certify that quotes are exact or that all available openings
were found. Unknown dates, model mistakes, fees, eligibility and supervisor
availability still need review. Results can expire after their check date.

## Website setup

Under **Settings → Pages**, set the source to **GitHub Actions**. The initial
`Publish results website` workflow deploys `docs/`. The search workflow deploys
updated results directly after a successful search. If repository policies block
Actions writes or Pages, a repository administrator must approve those permissions.

All files in `data/` and the website are public. Do not add applicant profiles,
private correspondence, CVs or other personal data. Unverified raw discovery
notes remain excluded from the published data.

## Tests and limitations

Eight deterministic tests cover domain validation, evidence membership,
conditional funding and date gates. They are not an evaluation of search recall
or factual accuracy. The agent does not independently crawl every university,
automatically expand the institution list, or run continuously.