SVB episode: peak crash probability vs. realized drawdown per asset. Regenerate with `doit svb_case_study`.

## Data Dictionary

- **ticker**: `str`, SIVB, KRE, or XLF.
- **level**: `str`, name / sector / systemic.
- **peak_pstar**: `float64`, peak risk-neutral 20% crash probability during the episode.
- **peak_lower**: `float64`, the lower bound at that peak.
- **peak_date**: `datetime64[ns]`, the date of the peak.
- **realized_drawdown**: `float64`, return from the 8 March close to the March trough.
- **crashed**: `bool`, whether the drawdown breached −20%.
