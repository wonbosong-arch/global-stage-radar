# EXAONE Japan 100-stock official-source pilot (2026-11-10)

## Scope and provenance

Focus: 100 TOPIX Core30 (30) and Large70 (70) member companies, **no market-cap threshold**. This task surveys exchange-provided **industry index data** and **stock-specific sector classifications**, not the stock records themselves.

Official JPX source pointers, checked by GPT **before the EXAONE call**:

| Data category | JPX official evidence | What is supported | Current limitation |
| --- | --- | --- | --- |
| 33 industry sector index series | [JPX current index values](https://www.jpx.co.jp/english/markets/indices/realvalues/) | A dedicated TOPIX Sector Indices (33-sector) table and online chart | Value table can require browser JavaScript; **no validated machine-download feed** |
| TOPIX-17 index series | Same JPX current index values page and [official factsheet dated 2025-08-29](https://www.jpx.co.jp/english/markets/indices/factsheets/files/e_000_fac2_sector.pdf) | 33 SICC industries grouped into 17 sector indices | This is not a company's ETF holdings file |
| Historical industry index levels | [JPX recent index history](https://www.jpx.co.jp/english/markets/indices/realvalues/) | Official site advertises past **5 business days**; see [JPX paid historical products](https://www.jpx.co.jp/english/markets/paid-info-equities/historical/index.html) for extended OHLC | Free, licensed, long historical series **not established** |
| Stock code, English name, 33/17 sector | [JPX monthly TSE-listed issues file page](https://www.jpx.co.jp/english/markets/statistics-equities/misc/01.html) | Previous-month-end Excel; includes code, company, 33/17 codes/names, TOPIX size bucket. Updated around third business day of each month | Contents and exact Core30=30, Large70=70 on the chosen effective date **not downloaded or checked here** |
| Alternative security master | [JPX J-Quants equity master spec](https://jpx-jquants.com/en/spec/eq-master) | Explicit `CoNameEn`, `S33`, `S17`, `ScaleCat` | Access tiers and separate service terms; no EXAONE access to J-Quants account |
| ETF correspondence | [JPX Japan equity sector ETF listing](https://www.jpx.co.jp/english/equities/products/etfs/issues/01-03.html) | Lists NEXT FUNDS TOPIX-17 ETFs, including 1617–1633 | ETF index exposure is not verified individual ETF holdings |

**JPX redistribution restriction:** [JPX terms](https://www.jpx.co.jp/english/term-of-use/) do not authorize commercial collection or secondary use without permission or a contract. This pilot neither scrapes JPX, downloads security master files, nor exports underlying daily index levels. The web-visible official citations do not themselves grant redistribution rights.

## Actual EXAONE delegation

New narrow GitHub Actions workflow: `.github/workflows/exaone-japan-source-audit.yml`. API logic: `automation/exaone_japan_source_pilot.py`.

- The trusted input consists of 6 cited JPX/public-service source descriptions **researched by GPT**. EXAONE independently summarizes and differentiates official 33-sector index availability, TOPIX-17, daily-history access, official company-sector codes, and licensing. This is **not autonomous browser research**, since EXAONE receives evidence instead of being given a network browser or data-download tools.
- Opt-in manual `workflow_dispatch`; `live` defaults to false. On `live=true`, exactly **one** EXAONE model API call is attempted without retry. Workflow can neither write code nor push to GitHub.
- A strict schema accepts four evidence-backed report topics, rejects invented IDs or extra company/price fields. Output labels stay `unverified_model_report_for_human_review`, `topix100_company_records_verified=0`, and `actual_index_values_downloaded=0`.
- The script records success or failure in the CI run, duration of successful calls, provider-**reported** prompt/completion/total/reasoning tokens (or `미확인`), and selected rate-limit headers when provided. Raw response, bearer token, complete headers, unbounded model text and exception bodies are not logged. No secrets are included in the artifact.
- Artifact `exaone-japan-official-sector-source-audit` is review-only, available for three days after a successful live run. No auto-PR, merge or dashboard activation.
- Max **1 call per manual run**; the user's total pilot budget is **30 calls** across future runs, not the provider's official quota. This workflow is never scheduled; cumulative runs require external tracking. Missing headers are recorded as `미확인`.

To run once after **PR review and explicit integration approval**: GitHub Actions > EXAONE Japan official-sector source audit > select `data-validation-mvp` > `live=true` > Run workflow. This requires the new workflow to be present on the runnable integration branch. It is not triggered merely by opening this PR.

## Existing research and separation

Prior [PR #234](https://github.com/wonbosong-arch/global-stage-radar/pull/234) is GPT-authored, draft, not EXAONE output. It contains a **private-input offline validator** and synthetic tests, but does not prove that 100 official Japanese stocks have been validated. It remains separate. Existing Japan ETF price collection and 1617–1633 proxy work are reused as background and not edited.

No edits to `main`, US stock code, Japan operational ETF files, Stage engine, dashboard or secrets. No public upload of JPX index level histories or company-level derived mapping.

## Interpretation and exit criteria

**Research verified by GPT now:** JPX officially offers 33 and 17 sector index series and official per-stock 33/17 industry classification via the monthly master; recent online index history is explicitly 5 business days, longer OHLC under separate historical products.

**Not yet done:** EXAONE live model call, API usage measurement, retrieval of individual index values/daily history, confirmation of 100 exact stock identities and licensed data-processing rights. PR CI success tests only our **offline** workflow/client and simulated model report. A real EXAONE run is required before attributing any generated findings to the model.

The next scope decision is whether user can lawfully process JPX's monthly master and a long index-history feed for a private research-only workflow. No unapproved collection or activation.
