Month-end S&P 500 constituent panel mapped to OptionMetrics `secid` via the CRSP–OptionMetrics link. Regenerate with `doit build_secid_universe`.

## Data Dictionary

- **date**: `datetime64[ns]`, last NYSE trading day of the month (the formation
  date on which membership is evaluated).
- **permno**: `int64`, CRSP permanent security identifier of an S&P 500 member
  on `date`.
- **secid**: `Int64` (nullable), OptionMetrics security id linked to the permno;
  null when the member has no valid CRSP–OptionMetrics link that month.
- **score**: `Int64` (nullable), WRDS link match quality (1 = best); null when
  `secid` is null.
- **carried_forward**: `bool`, True when the row falls past the CRSP constituent
  vintage and its membership was frozen from the last known date; always False in
  paper-exact replication.
