# China mainland ETF identity audit — research only

Date: 2026-10-30
Base: data-validation-mvp

## Scope and safeguards

- Continue the existing mainland-China 30-candidate research without fetching new KIS bars.
- Do not modify active ETF universe, scheduled collection, Stage logic, price snapshots, or the deployed dashboard.
- PR #181 separately corrects SSE 512600's issuer attribution; do not duplicate its edits.

## Findings from current repository metadata

1. The coverage matrix records 30 mainland Shanghai ETF candidates as research-only, with price observations already collected. It explicitly flags 512620's identity and shorter history for further review.
2. The current country_sector_proxy_candidates.csv contains a China row for 512600 with a provisional ChinaAMC attribution; PR #181 proposes correcting it to Harvest using an official HKEX notice. Treat the pending PR as the owner of this correction.
3. The current country_sector_proxy_candidates.csv does **not** contain a 512620 row. Do not interpret absence as delisting or invent a candidate mapping.
4. The existing coverage matrix treats 512760 as a specialist semiconductor exposure and 515030 as a new-energy-vehicle theme, not broad information-technology or energy-sector benchmarks.

## Required independent evidence before activation

For each candidate, record symbol, exchange, exact fund name (Chinese and English if officially available), issuer, tracked index, effective listing status, source URL and document date, quote history length, benchmark suitability, Korean broker tradability and data-use rights. Unverified attributes must be marked unknown, not inferred from a similar symbol.

## Immediate next actions

- Locate 512620 in existing research snapshots and verify its official SSE/issuer record before creating or changing a production candidate row.
- Complete the remaining 29 identity checks while PR #181 handles 512600.
- Keep all unapproved mainland candidates inactive; only validated mappings may proceed to an implementation PR.

This document records repository-grounded review status, **not** a completed independent verification of official external records.
