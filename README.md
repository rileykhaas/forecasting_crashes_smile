forecasting_crashes_smile
=========================

A reproducible analytical pipeline (RAP) that replicates — and extends — Martin & Shi
(2025), "Forecasting Crashes with a Smile."

## About this project

Martin & Shi (2025) show that the shape of the option-implied volatility smile carries a
model-free signal about the probability that a stock, or the market, crashes. From option
prices alone they derive a **lower bound** (and an upper bound) on the *physical* probability
that the gross return over the next τ months falls at or below a crash threshold q — for
example a 20% drop (q = 0.80) over one month. The lower bound is the headline result: it
forecasts crashes both in and out of sample, for the S&P 500 index and for individual
constituents (financial firms included), with no free parameters to estimate.

This repository rebuilds that result end-to-end and pushes it past the paper's sample:

- **Replication.** Reproduce the paper's Table 1 (summary statistics), Table 2 (calibration
  regressions), and Figures 1, 2, and 6 over the original 1996–2022 window, with unit tests
  that pin our numbers to the paper within a stated tolerance.
- **Updated numbers.** Re-run every exhibit with the sample extended to the most recent data
  available (through 2025), so the bound's forecasting record can be read on fresh data.
- **A product, not just a replication.** Alongside the replication we ship (a) a cleaned,
  documented firm-month panel of S&P 500 constituents with their option-implied crash bounds,
  (b) `crashbounds`, a small pip-installable package exposing the core math, and (c) our own
  exploratory exhibits — a summary-statistics table and figures that characterize the data.
- **Extensions.** Crash bounds for the SPDR sector ETFs, and a Silicon Valley Bank
  (March 2023) case study that reads the bound against a real idiosyncratic crash.

**Data.** Option-implied volatility surfaces and risk-free rates from **OptionMetrics**;
S&P 500 index constituents, the CRSP–OptionMetrics link, and stock prices / returns / volume /
shares from **CRSP** — all accessed via **WRDS**. The raw data is proprietary and is never
committed to git; see `docs_src/site/project_overview/data_sources.md`.

**Method (the A1–A5 engine).** risk-neutral CDF via Breeden–Litzenberger → risk-neutral crash
probability → fear correction (γ = 2) → Fréchet–Hoeffding copula bounds → assembled results
table. The fixed parameters (γ, horizons τ ∈ {1, 3, 6, 12} months, thresholds
q ∈ {0.70, 0.80, 0.90}, the S&P 500 index secid `108105`) and every cleaned-table schema live
in `src/schema.py`, the single source of truth — refer to it rather than duplicating them.

**Team.** Riley Haas and Marija Jovicic.

## Roadmap & task tracking

Detailed tasks live in **GitHub Issues** (the live task board, with assignees), grouped into
milestones. This is the map:

- **M0 — Foundations:** WRDS pulls, the firm-month panel, and the A1–A5 crash-probability
  engine.
- **M1 — Replication:** Tables 1–2 and Figures 1, 2, 6 on the paper's window, plus the
  exploratory-data product.
- **M2 — Package:** `crashbounds` — scaffold, a public API over A1–A4, and tests + CI.
- **M3 — Extensions & SVB:** the date extension to the present, sector-ETF bounds, and the SVB
  case study.
- **M4 — Integration:** chartbook manifests + LaTeX report wiring, the notebook tour, and the
  end-to-end `doit` clean run.

### Task list & ownership

Each task below is a GitHub issue. **Owner** is the team member primarily responsible (fill in
to match the issue assignee); tasks can be shared, and both members review everything.

**M0 — Foundations**

| Issue | Task | Owner |
|-------|------|-------|
| [#14](https://github.com/rileykhaas/forecasting_crashes_smile/issues/14) | CRSP: `pull_sp500.py` + `pull_link.py` → resolved secid universe | Riley |
| [#15](https://github.com/rileykhaas/forecasting_crashes_smile/issues/15) | CRSP: `realized_returns.py` → `realized_returns.parquet` | Marija |
| [#16](https://github.com/rileykhaas/forecasting_crashes_smile/issues/16) | OptionMetrics: `pull_optionmetrics.py` → raw `vsurfd` + `securd` + `zerocd` | Riley |
| [#17](https://github.com/rileykhaas/forecasting_crashes_smile/issues/17) | OptionMetrics: `clean_surface.py` + `rates.py` → `clean_surface.parquet` + `rates.parquet` | Riley |
| [#18](https://github.com/rileykhaas/forecasting_crashes_smile/issues/18) | Engine A1+A2: `rnd.py` risk-neutral CDF + `crash_prob.py` risk-neutral crash prob | Marija |
| [#19](https://github.com/rileykhaas/forecasting_crashes_smile/issues/19) | Engine A3+A4: `utility_correction.py` + `bounds.py` | Marija |
| [#20](https://github.com/rileykhaas/forecasting_crashes_smile/issues/20) | Engine A5: `run_pipeline.py` → `results.parquet` + dodo wiring | Marija |
| [#21](https://github.com/rileykhaas/forecasting_crashes_smile/issues/21) | Engine tests + doctests (extend `test_schema.py`) | Marija |

**M1 — Replication**

| Issue | Task | Owner |
|-------|------|-------|
| [#22](https://github.com/rileykhaas/forecasting_crashes_smile/issues/22) | Figure 1 — AAPL & AIG single-name bounds | Riley |
| [#23](https://github.com/rileykhaas/forecasting_crashes_smile/issues/23) | Figure 2 — cross-sectional medians + SPX index prob | Riley |
| [#24](https://github.com/rileykhaas/forecasting_crashes_smile/issues/24) | Table 1 — summary statistics (lower / P\* / upper / realized) | Riley |
| [#25](https://github.com/rileykhaas/forecasting_crashes_smile/issues/25) | Table 2 — regression calibration tests (beta, alpha, R²) | Riley |
| [#26](https://github.com/rileykhaas/forecasting_crashes_smile/issues/26) | Figure 6 — out-of-sample R² vs naive benchmark | Riley |
| [#33](https://github.com/rileykhaas/forecasting_crashes_smile/issues/33) | EDA product — summary-stats table + figures of the underlying panel | Riley |

**M2 — Package (`crashbounds`)**

| Issue | Task | Owner |
|-------|------|-------|
| [#27](https://github.com/rileykhaas/forecasting_crashes_smile/issues/27) | Package scaffold + `pyproject.toml` | Marija |
| [#28](https://github.com/rileykhaas/forecasting_crashes_smile/issues/28) | Public API wrapping A1–A4 | Marija |
| [#29](https://github.com/rileykhaas/forecasting_crashes_smile/issues/29) | Tests + CI + README quickstart | Marija |

**M3 — Extensions & SVB**

| Issue | Task | Owner |
|-------|------|-------|
| [#30](https://github.com/rileykhaas/forecasting_crashes_smile/issues/30) | Extend `END_DATE` → 2025-12-31; both re-pull, regenerate | Riley & Marija |
| [#31](https://github.com/rileykhaas/forecasting_crashes_smile/issues/31) | SVB case study — spike & decide (daily feasibility, presentation) | Riley |
| [#34](https://github.com/rileykhaas/forecasting_crashes_smile/issues/34) | Sector ETF extension — all SPDR sector ETF bounds | Riley |

**M4 — Integration**

| Issue | Task | Owner |
|-------|------|-------|
| [#32](https://github.com/rileykhaas/forecasting_crashes_smile/issues/32) | chartbook manifests + LaTeX wiring + full `doit` clean run | Riley & Marija |
| [#35](https://github.com/rileykhaas/forecasting_crashes_smile/issues/35) | Notebook tour — cleaned data + analysis walkthrough (`docs_src`) | Riley |
| [#36](https://github.com/rileykhaas/forecasting_crashes_smile/issues/36) | LaTeX narrative — overview, successes/challenges, data sources | Riley |

## Quick Start

The quickest way to run code in this repo is to use the following steps.

You must have TexLive (or another LaTeX distribution) installed on your computer and available in your path.
You can do this by downloading and installing it from here ([windows](https://tug.org/texlive/windows.html#install)
and [mac](https://tug.org/mactex/mactex-download.html) installers).


First, you must have the `conda` package manager installed (e.g., via Anaconda). However, I recommend using `mamba`, via [miniforge](https://github.com/conda-forge/miniforge) as it is faster and more lightweight than `conda`.

Create and activate the conda environment:
```bash
conda env create -f environment.yml
conda activate forecasting_crashes_smile
```

This project pulls proprietary data from **WRDS** (OptionMetrics and CRSP), so you need a WRDS
account. Copy `.env.example` to `.env` and set your `WRDS_USERNAME`:
```bash
cp .env.example .env   # then edit .env and set WRDS_USERNAME
```
On the first WRDS connection you will be prompted for your password and offered to create a
`~/.pgpass` file, so later runs authenticate automatically.

Finally, run the whole project end-to-end (pulls, cleaning, the engine, every exhibit, the
report, the chartbook, and the tests):
```bash
doit
```
The first run downloads all the data and can take a while; afterwards `doit` only re-runs what
has changed. Outputs land in `_output/` (figures, tables, the report PDF) and `docs/` (the
chartbook site).


### Other commands

#### Unit Tests and Doc Tests

You can run the unit test, including doctests, with the following command:
```
pytest --doctest-modules
```

You can (re)build the chartbook documentation site on its own with:
```bash
doit build_chartbook_site
```
The site is written to `docs/`; open `docs/index.html` to view it. The full `doit` run
builds it as well.


#### Setting Environment Variables

You can [export your environment variables](https://stackoverflow.com/questions/43267413/how-to-set-environment-variables-from-env-file)
from your `.env` files like so, if you wish. This can be done easily in a Linux or Mac terminal with the following command:
```bash
set -a  # automatically export all variables
source .env
set +a
```
On Windows (PowerShell):
```powershell
Get-Content .env | ForEach-Object { if ($_ -match '^([^=]+)=(.*)$') { [Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process') } }
```

### Formatting

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting Python code.

```bash
# Auto-fix linting issues (e.g., unused imports, undefined names)
ruff check . --fix

# Format code (consistent style, spacing, line length)
ruff format .

# Sort imports, then fix linting issues, then format
ruff format . && ruff check --select I --fix . && ruff check --fix .
```

- `ruff check --fix` applies safe auto-fixes for linting violations
- `ruff format` formats code similar to Black
- `--select I` targets only import sorting rules (isort-compatible)

### Repository layout

- **`src/`** — all Python: the WRDS pulls, the cleaning steps, the A1–A5 engine, and the
  exhibit scripts, each with a co-located `test_*.py`. `src/settings.py` resolves configuration
  and directory paths; `src/schema.py` is the single source of truth for constants and table
  schemas.
- **`dodo.py`** — the [PyDoit](https://pydoit.org/) task graph that runs the whole project
  end-to-end (it works like a `Makefile`, but in Python). Run everything with `doit` from the
  repository root.
- **`_data/`** — cached data: the raw WRDS pulls and the cleaned parquet tables. Generated by
  the pipeline and **not** tracked in Git; safe to delete and rebuild.
- **`_output/`** — generated exhibits: `results.parquet`, the figures and tables, the rendered
  notebook, and the compiled report. Also generated by the pipeline; safe to delete.
- **`reports/`** — the LaTeX source for the write-up (`report.tex`) and its style files.
- **`docs_src/`** — chartbook source: a markdown page for each chart and dataframe, plus the
  project-overview site pages.
- **`docs/`** — the built chartbook website (produced by `doit build_chartbook_site`).
- **`data_manual/`** — data that cannot be regenerated from code; this folder *is* tracked in Git.
- **`assets/`** — static images not generated from code (e.g. hand-drawn figures).
- **`.env`** — machine-specific settings such as your WRDS username and any custom data paths.
  Not tracked in Git; copy `.env.example` to `.env` and fill it in.

### Data and output storage

- **`_data/`** holds cached data: the raw WRDS pulls and the cleaned parquet tables. It is
  **not** tracked in Git — every file is recreated by running `doit` (the pull tasks live in
  `dodo.py`), so the folder can be deleted and rebuilt at any time. The raw OptionMetrics and
  CRSP data is proprietary and must never be committed.
- **`_output/`** holds everything generated from code: dataframes, figures, tables, the
  rendered notebook, the compiled report, and the chartbook site inputs. It, too, is fully
  reproducible and safe to delete.
- **`data_manual/`** holds any data that *cannot* be regenerated from code; because it would be
  costly to lose, it is kept under version control.

The locations of `_data/` and `_output/` are configurable through environment variables in
`.env`. `src/settings.py` loads and preprocesses those variables and exposes them through a
`config` object, which every script imports rather than hard-coding paths.

### Naming Conventions

 - **`pull_` vs `load_`**: Files or functions that pull data from an external
 data source are prepended with "pull_", as in "pull_fred.py". Functions that
 load data that has been cached in the "_data" folder are prepended with "load_".
 For example, inside of the `pull_CRSP_Compustat.py` file there is both a
 `pull_compustat` function and a `load_compustat` function. The first pulls from
 the web, whereas the other loads cached data from the "_data" directory.


### Dependencies and Virtual Environments

#### Working with `conda` environments

This project uses conda for environment management. The dependencies are stored in `environment.yml`.

To create/update the environment:
```bash
conda env create -f environment.yml
# or to update an existing environment:
conda env update -f environment.yml
```

To activate the environment:
```bash
conda activate forecasting_crashes_smile
```

To export the current environment:
```bash
conda env export > environment.yml
```

**Tip:** Consider using `mamba` instead of `conda` for faster package resolution. Install via [miniforge](https://github.com/conda-forge/miniforge).
