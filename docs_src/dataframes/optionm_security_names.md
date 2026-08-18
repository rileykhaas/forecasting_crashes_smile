OptionMetrics security-name history (`secnmd`): ticker, issuer, and SIC per name spell. Regenerate with `doit pull_optionmetrics`.

## Data Dictionary

- **secid**: `int64`, OptionMetrics security id.
- **ticker**: `str`, ticker symbol in effect for this name spell.
- **issuer**: `str`, issuing-company description.
- **issue**: `str`, issue description.
- **cusip**: `str`, CUSIP for this spell.
- **class**: `str`, share-class designator.
- **sic**: `str`, SIC industry code.
- **effect_date**: `datetime64[ns]`, first date this name spell is in effect.
