Industry proxy vs. direct sector-ETF bound, and each measure's gap to realized, for all eleven Select Sector SPDR sectors (one-year 20% crash). Regenerate with `doit industry_compare`.

## Data Dictionary

- **sector**: `str`, the GICS / Select Sector SPDR sector (the paper's FF49 industries rolled up).
- **ticker**: `str`, the sector's Select Sector SPDR ETF.
- **clean**: `bool`, whether the FF49→GICS mapping is unambiguous (True) or a best-fit approximation (False).
- **proxy_lower**: `float64`, mean equal-weighted constituent lower bound (the paper's Figure-10 FF49 proxy).
- **direct_lower**: `float64`, mean sector-ETF lower bound (direct measure).
- **realized_freq**: `float64`, realized frequency of a 20% crash over the next year.
- **proxy_gap**: `float64`, the proxy's distance from realized (`proxy_lower − realized_freq`).
- **direct_gap**: `float64`, the direct measure's distance from realized (`direct_lower − realized_freq`).
