# Nasdaq single-source private US review

`nasdaq_single_source.py` extends the existing PR218 parser, rather than adding a
collector or another vendor adapter. Nasdaq's native Sector and Industry are the
only classification observations in this path. KIS remains the listing identity
and price source; existing market-value provenance and the $1B screen are reused.
This command is an offline research report, not an approval/activation payload.

## Input and privacy

Supply the user's manually downloaded Stock Screener CSV once a month. The
actual intake supports Symbol, Name, Sector, Industry, Market Cap without an
Exchange column. Reuse `read_table`, missing-value handling, venue normalization,
and explicit same-class aliases from `nasdaq_local_csv_review.py`. Its older
strict exchange/permission-manifest command is unchanged; its historical access
audit is not a current measurement of a subsequently supplied file.

Raw files, manifests and all enterprise-level reports must stay outside every
Git checkout and the source directory. No real rows or derived enterprise data
are fixtures, commit inputs, CI artifacts or PR attachments. The CLI requires a
new private output path, refuses overwrites, and prints only aggregate counts.
Do not redirect detailed reports into a public checkout. The implementation
has no downloader, network client, scheduled job or registry write.

The manifest records the user's supplied-file private noncommercial offline
instruction and exact CSV hash. It does not certify a license or confer rights.
Unknown provider dates and download UTC stay null; filesystem timestamps or the
filename never fill them. Known dates need their own references; a known source
classification date after the requested evaluation date is rejected. The
source date can remain unknown for current private analysis, which therefore
does not claim point-in-time/backtest classification validity.

Example provenance structure (replace the hash and instruction reference):

```json
{
  "dataset_kind": "user_supplied_nasdaq_csv",
  "acquisition_method": "user_manual_download",
  "scope": "private_noncommercial_offline",
  "user_instruction_reference": "Reference to the user's supplied-file instruction",
  "csv_sha256": "SHA256_OF_PRIVATE_CSV",
  "source_url": "https://www.nasdaq.com/market-activity/stocks/screener",
  "source_as_of": null,
  "downloaded_at_utc": null
}
```

```text
python nasdaq_single_source.py --csv PRIVATE/input.csv --manifest PRIVATE/manifest.json --as-of YYYY-MM-DD --output PRIVATE/new-review.json
```

## Identity and exception handling

1. Require a unique US registry symbol across KIS NAS/NYS/AMS venues. Assess the
   retained KIS master/discovery type and venue with the existing
   `assess_candidates`; no external issuer lookup is a routine prerequisite.
2. Join a unique CSV symbol. A missing CSV Exchange is recorded as unknown;
   KIS's stored venue supplies listing context and is never described as an
   independently verified Nasdaq venue. If Exchange exists, require agreement.
3. Compare normalized issuer-name tokens with KIS registry/master names. Legal
   and security descriptors are removed, and only distinctive bounded name
   prefixes accommodate KIS truncation. Unrelated names and short generic
   prefixes are held; there is no fuzzy-score threshold or name-based sector
   inference. Share-class and security-type checks are separate from name cleanup.
4. Retain suffixes and preferred/warrant signals. Same-class notation aliases
   require explicit evidence and KIS venue; automatic punctuation stripping,
   cross-class collapse, duplicate master/source rows and alias collisions are
   rejected or held. Source ADR signals retain the existing ratio requirement.

Native classification joining, ETF proxy suitability and Stage data readiness
are separate report fields. An uncertain proxy does not erase the native
observation or valid price-only MA30/slope diagnostics. A price-only diagnostic
has no Stage label: the established Stage engine still needs market/sector RS.

## Explicit ETF proxy policy

`RULES` in the implementation is the versioned exact Sector+Industry allowlist.
It uses precisely XLB/XLC/XLE/XLF/XLI/XLK/XLP/XLRE/XLU/XLV/XLY. These are research
proxies, not a declaration that Nasdaq's taxonomy equals GICS. No blanket
sector-only rule, ticker exception list, KIS industry-code decoder or fallback
vendor classification is used. `OVERRIDES` expresses the explicit
Industrials+Auto Manufacturing -> Consumer Discretionary/XLY rule.

Unknown industry pairs, Miscellaneous, blank checks, broad REIT/software/EDP and
ambiguous equipment groups are review-only. For example the broad REIT label
cannot distinguish mortgage REITs, and broad software/EDP can include media or
gaming. Semiconductors, when otherwise clear, use the broad XLK proxy in this
11-ETF path. An existing SOXX or other differing stored/curated mapping becomes
a visible conflict; it is never silently replaced. Rule expansion is a separate
code review using native industry semantics, not mass external issuer checking.

Validate each ETF against the existing active KIS sector-ETF metadata. Existing
stored and curated suggestions are read only for conflict detection and market
benchmark context, never to supply a missing native sector.

## Replay and comparison

Reuse `evaluate_new_rows`, `cap_provenance`, `OfflineStageReplay`, completed
weekly bars, MA30/slope, 26-week market/sector RS, freshness and `classify_stage`.
The original $1B filter, KIS identity, valid OHLC/volume, duplicate/future-date
checks, 150 valid daily rows and 35 completed weeks remain in force. Nasdaq Last
Sale and Market Cap never substitute for retained prices or the selected cap.

Exclude the saved 85 from additions. Preserve their historical labels separately,
and re-evaluate those 85 with their saved mappings on the current price snapshot
and the same requested date used for additions. Only these current results may
be combined. Historical counts are never added to current labels. Missing or
invalid inputs can reduce the current baseline; the report shows that explicitly.

`additional_eligible` and labels mean actual execution of this versioned private
review policy. They do not mean official GICS correctness, source-date certainty,
new operational additions or deployment. Earlier exploratory counts from a
blanket sector crosswalk are not this policy's validated measurements.

## Verification and operational boundary

Synthetic tests exercise Exchange absence/conflict, names, class aliases and
collisions, securities/ADR checks, unknown industries, proxy/metadata conflicts,
unchanged cap/price gates, private paths and the same-date baseline replay.
No actual external enterprise records are embedded in the tests.

Keep PR218 Draft against data-validation-mvp. No main/integration commits,
merges, production dashboard/activation changes, live KIS, accounts, secrets,
paid services, collection, cron or Actions configuration changes are part of
this work. Existing automatic PR CI alone validates the source changes.
