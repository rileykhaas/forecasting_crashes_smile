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
| [#14](https://github.com/rileykhaas/forecasting_crashes_smile/issues/14) | CRSP: `pull_sp500.py` + `pull_link.py` → resolved secid universe |  |
| [#15](https://github.com/rileykhaas/forecasting_crashes_smile/issues/15) | CRSP: `realized_returns.py` → `realized_returns.parquet` |  |
| [#16](https://github.com/rileykhaas/forecasting_crashes_smile/issues/16) | OptionMetrics: `pull_optionmetrics.py` → raw `vsurfd` + `securd` + `zerocd` |  |
| [#17](https://github.com/rileykhaas/forecasting_crashes_smile/issues/17) | OptionMetrics: `clean_surface.py` + `rates.py` → `clean_surface.parquet` + `rates.parquet` |  |
| [#18](https://github.com/rileykhaas/forecasting_crashes_smile/issues/18) | Engine A1+A2: `rnd.py` risk-neutral CDF + `crash_prob.py` risk-neutral crash prob |  |
| [#19](https://github.com/rileykhaas/forecasting_crashes_smile/issues/19) | Engine A3+A4: `utility_correction.py` + `bounds.py` |  |
| [#20](https://github.com/rileykhaas/forecasting_crashes_smile/issues/20) | Engine A5: `run_pipeline.py` → `results.parquet` + dodo wiring |  |
| [#21](https://github.com/rileykhaas/forecasting_crashes_smile/issues/21) | Engine tests + doctests (extend `test_schema.py`) |  |

**M1 — Replication**

| Issue | Task | Owner |
|-------|------|-------|
| [#22](https://github.com/rileykhaas/forecasting_crashes_smile/issues/22) | Figure 1 — AAPL & AIG single-name bounds |  |
| [#23](https://github.com/rileykhaas/forecasting_crashes_smile/issues/23) | Figure 2 — cross-sectional medians + SPX index prob |  |
| [#24](https://github.com/rileykhaas/forecasting_crashes_smile/issues/24) | Table 1 — summary statistics (lower / P\* / upper / realized) |  |
| [#25](https://github.com/rileykhaas/forecasting_crashes_smile/issues/25) | Table 2 — regression calibration tests (beta, alpha, R²) |  |
| [#26](https://github.com/rileykhaas/forecasting_crashes_smile/issues/26) | Figure 6 — out-of-sample R² vs naive benchmark |  |
| [#33](https://github.com/rileykhaas/forecasting_crashes_smile/issues/33) | EDA product — summary-stats table + figures of the underlying panel |  |

**M2 — Package (`crashbounds`)**

| Issue | Task | Owner |
|-------|------|-------|
| [#27](https://github.com/rileykhaas/forecasting_crashes_smile/issues/27) | Package scaffold + `pyproject.toml` |  |
| [#28](https://github.com/rileykhaas/forecasting_crashes_smile/issues/28) | Public API wrapping A1–A4 |  |
| [#29](https://github.com/rileykhaas/forecasting_crashes_smile/issues/29) | Tests + CI + README quickstart |  |

**M3 — Extensions & SVB**

| Issue | Task | Owner |
|-------|------|-------|
| [#30](https://github.com/rileykhaas/forecasting_crashes_smile/issues/30) | Extend `END_DATE` → 2025-12-31; both re-pull, regenerate |  |
| [#31](https://github.com/rileykhaas/forecasting_crashes_smile/issues/31) | SVB case study — spike & decide (daily feasibility, presentation) |  |
| [#34](https://github.com/rileykhaas/forecasting_crashes_smile/issues/34) | Sector ETF extension — all SPDR sector ETF bounds |  |

**M4 — Integration**

| Issue | Task | Owner |
|-------|------|-------|
| [#32](https://github.com/rileykhaas/forecasting_crashes_smile/issues/32) | chartbook manifests + LaTeX wiring + full `doit` clean run |  |
| [#35](https://github.com/rileykhaas/forecasting_crashes_smile/issues/35) | Notebook tour — cleaned data + analysis walkthrough (`docs_src`) |  |
| [#36](https://github.com/rileykhaas/forecasting_crashes_smile/issues/36) | LaTeX narrative — overview, successes/challenges, data sources |  |

Both team members are expected to understand the whole project — the week-10 oral defense is
graded individually.

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

Finally, run the project tasks:
```bash
doit
```
And that's it!


### Other commands

#### Unit Tests and Doc Tests

You can run the unit test, including doctests, with the following command:
```
pytest --doctest-modules
```

You can build the documentation with:
```
rm ./src/.pytest_cache/README.md
jupyter-book build -W ./
```
Use `del` instead of rm on Windows


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

### General Directory Structure

 - The `assets` folder is used for things like hand-drawn figures or other
   pictures that were not generated from code. These things cannot be easily
   recreated if they are deleted.

 - The `_output` folder, on the other hand, contains dataframes and figures that are
   generated from code. The entire folder should be able to be deleted, because
   the code can be run again, which would again generate all of the contents.

 - The `data_manual` is for data that cannot be easily recreated. This data
   should be version controlled. Anything in the `_data` folder or in
   the `_output` folder should be able to be recreated by running the code
   and can safely be deleted.

 - I'm using the `doit` Python module as a task runner. It works like `make` and
   the associated `Makefile`s. To rerun the code, install `doit`
   (https://pydoit.org/) and execute the command `doit` from the `src`
   directory. Note that doit is very flexible and can be used to run code
   commands from the command prompt, thus making it suitable for projects that
   use scripts written in multiple different programming languages.

 - I'm using the `.env` file as a container for absolute paths that are private
   to each collaborator in the project. You can also use it for private
   credentials, if needed. It should not be tracked in Git.

### Data and Output Storage

I'll often use a separate folder for storing data. Any data in the data folder
can be deleted and recreated by rerunning the PyDoit command (the pulls are in
the dodo.py file). Any data that cannot be automatically recreated should be
stored in the "data_manual" folder. Because of the risk of manually-created data
getting changed or lost, I prefer to keep it under version control if I can.
Thus, data in the "_data" folder is excluded from Git (see the .gitignore file),
while the "data_manual" folder is tracked by Git.

Output is stored in the "_output" directory. This includes dataframes, charts, and
rendered notebooks. When the output is small enough, I'll keep this under
version control. I like this because I can keep track of how dataframes change as my
analysis progresses, for example.

Of course, the _data directory and _output directory can be kept elsewhere on the
machine. To make this easy, I always include the ability to customize these
locations by defining the path to these directories in environment variables,
which I intend to be defined in the `.env` file, though they can also simply be
defined on the command line or elsewhere. The `settings.py` is responsible for
loading these environment variables and doing some preprocessing on them.
The `settings.py` file is the entry point for all other scripts to these
definitions. That is, all code that references these variables and others are
loaded by importing `config`.

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
