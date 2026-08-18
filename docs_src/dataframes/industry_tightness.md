Industry proxy vs. direct sector-ETF bound, and each measure's gap to realized. Regenerate with `doit industry_compare`.

## Data Dictionary

- **ff_industry**: `str`, FF12 industry code (Money, Enrgy, Utils, Hlth, BusEq, Manuf).
- **sector**: `str`, short industry label.
- **ticker**: `str`, the matched Select Sector SPDR ETF.
- **proxy_lower**: `float64`, mean equal-weighted constituent lower bound (Figure-10 proxy).
- **direct_lower**: `float64`, mean sector-ETF lower bound (direct measure).
- **realized_freq**: `float64`, realized frequency of a 20% crash over 12 months.
- **proxy_gap**: `float64`, the proxy's distance from realized (`proxy_lower − realized_freq`).
- **direct_gap**: `float64`, the direct measure's distance from realized (`direct_lower − realized_freq`).
