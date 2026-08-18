## Description

An **original extension** (issue #31): the crash-bound machinery run at **daily**
frequency through the March 2023 collapse of Silicon Valley Bank, reading one event at
three levels. Built by `exhibit_svb.py` (task `svb_case_study`) from
`pull_svb_daily`'s three daily parquets — the same engine that prices the monthly
panel, run day by day.

Three stacked panels, each with the daily risk-neutral probability (red) and the
option-implied lower bound (blue) of a 20% one-month crash:

- **SIVB** — SVB Financial, the failed name (the crash itself);
- **KRE** — the regional-bank ETF (the sector layer);
- **XLF** — broad financials (the systemic layer).

The dashed line marks 10 March 2023, when regulators closed the bank and its options
were halted.

## What it shows

The exhibit works as a real-time classifier of contained vs. systemic. SIVB's crash
probability is quiet through February, drifts up in early March, then **explodes to
36%** on 9 March — its last trading day, after which the option surface simply ends
(the market stopped pricing it as a going concern). The stress then **decays sharply**
across the levels: KRE jumps to a **17.6%** peak on 17 March, while XLF reaches only
**6.1%**. That ordering — 36% → 18% → 6% — is the market pricing the event as
concentrated in the name and its sector, not systemic to the financial system. And for
SIVB's idiosyncratic crash, the risk-neutral sits above the (deliberately conservative)
lower bound, exactly as the theory predicts.

Regenerate with `doit svb_case_study` (after `doit pull_svb_daily`).
