# Candidate instrument classification policy

Status: conservative review policy; not a symbol-level approval list.

## Keep these concepts separate

- `market`: the trading market represented by the price series used in the dashboard.
- `exchange`: the exchange on which the exact instrument trades; use the provider's expected exchange code only after confirmation.
- `country`: issuer domicile / country exposure, which is not always the same as the listing market.
- `market_benchmark`: the benchmark used to compare the listed price series and relative strength.
- `sector_benchmark`: the sector ETF used for peer-relative strength; it can differ from the issuer's home-country market benchmark.
- `instrument_type`: common stock, ADR/ADS, or another instrument class. Do not infer this from the ticker alone.

## Specific review cases

### TSM (Taiwan Semiconductor Manufacturing ADS)
The queue records a verified depositary ratio of 5 ordinary shares per ADS and uses EWT for Taiwan-market context plus SOXX for semiconductor-sector context. These assignments do not independently validate KIS support, the market-cap convention, or the complete listing identity gate. Keep the candidate pending until those independent gates are resolved.

### BABA (Alibaba ADS)
The queue records a verified ratio of 8 ordinary shares per ADS and uses MCHI for China-market context plus XLY for the currently curated consumer-discretionary sector map. The sector mapping is a dashboard taxonomy choice, not a claim that all business exposure is U.S. domestic. Market-cap share-class convention and provider support remain separate review items.

### ETN and LIN (Irish-domiciled plc issuers with U.S. listings)
Do not force issuer domicile and trading market into one meaning. The current queue uses the U.S. trading market for price-source context, Ireland in the issuer-country field, and U.S. broad-market/sector ETF benchmarks. This is a provisional convention for a U.S.-listed price series, not a claim that the issuer is U.S.-domiciled. If the application later needs country exposure rather than legal domicile, add a separate explicit field rather than overloading `country`.

## Activation gate

Keep `activation_status=pending_review` until exact listing identity, issuer/listing-country treatment, benchmark mapping, market-cap evidence, and provider/history quality have separate evidence. Price rows returned for a requested ticker alone are not proof of the correct instrument.
