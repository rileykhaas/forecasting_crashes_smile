forecasting_crashes_smile
=========================

## About this project

Replication and extension of Martin & Shi (2025), "Forecasting Crashes with a Smile"

## Team & Task Division

The pipeline breaks into small, individually-claimable tasks. Each task has a
defined input and output, so they chain cleanly and can be signed up for one at
a time. Tick the box and add your initials when you take a task.

### Agree before anyone writes code

### Agreed constants and data conventions

Fixed parameters (from Martin & Shi 2025):
- Risk aversion: gamma = 2 (calibrated on market returns, Appendix C)
- Forecasting horizons: tau = 1, 3, 6, 12 months
- Crash thresholds: q = 0.70, 0.80, 0.90  (GROSS return levels, i.e. below 1;
  q = 0.80 = "down 20%" is the workhorse). Note: a rally extension, if added,
  would use q = 1.10, 1.20, 1.30 instead.
- Index secid: 108105 (S&P 500). Individual names: S&P 500 constituents.
- Frequency: last trading day of each month. Paper sample: Jan 1996 - Dec 2022
  (our extension pushes END_DATE to ~Aug 2025).

Join keys for the analysis-facing tables:
    date, secid, horizon_months, threshold_q

### Table schemas

**clean_surface.parquet**  (Slice 1) — one row per date x secid x maturity x strike-grid point
- date              last trading day of month (datetime)
- secid             int (108105 = index)
- days_to_maturity  int  (option maturity in calendar days; slices chosen to match
                          the 1/3/6/12-month horizons)
- moneyness         float  (K / S, strike over spot)
- implied_vol       float  (from OptionMetrics vol surface, after filtering +
                            flat extrapolation)
- spot_price        float  (S; constant within date x secid — carried here for convenience)

  Filtering (Appendix D): CRSP spot must exist; strike > 0; OptionMetrics
  dispersion in (0, 0.05); more than 10 distinct strikes per firm-month-maturity.
  Interpolation linear within observed strikes; flat extrapolation outside.

**rates.parquet**  (Slice 1) — one row per date x maturity  (index-level, not per-secid)
- date              datetime
- days_to_maturity  int
- zero_rate         float  (from OptionMetrics zero-coupon yield curve, linearly
                            interpolated across maturities)

**realized_returns.parquet**  (Slice 2) — one row per date x secid x horizon
                                (threshold-INDEPENDENT: stores the return, not the flag)
- date                   formation date = last trading day of month t
- secid                  int
- horizon_months         int in {1, 3, 6, 12}
- realized_gross_return  float  (R_{i, t -> t+tau}; GROSS, so 0.80 = down 20%;
                                 CRSP return with delisting returns integrated)

**results.parquet**  (Slice 3 / task A5) — one row per date x secid x horizon x threshold
- date                   datetime
- secid                  int
- horizon_months         int in {1, 3, 6, 12}
- threshold_q            float in {0.70, 0.80, 0.90}
- bound_lower            float  (P^L)
- prob_riskneutral       float  (P^*, the risk-neutral probability)
- bound_upper            float  (P^U)
- realized_gross_return  float  (joined from realized_returns for convenience)
- realized_flag          int    (= 1 if realized_gross_return <= threshold_q, else 0)

Invariant that a unit test should enforce: bound_lower <= prob_riskneutral <= bound_upper.

---

### Slice 1 — OptionMetrics surface

Pure OptionMetrics. No CRSP, no link table. Can start immediately.

- [ ] **S1a** — Pull IvyDB volatility surface (`vsurfd{year}`), zero curve (`zerocd`), secid lookups (`securd`/`secnmd`)  *(owner: __)*
- [ ] **S1b** — Filter surface using Martin & Shi's criteria (moneyness/maturity windows); flat-extrapolate beyond observed strikes  *(owner: __)*
- [ ] **S1c** — Write `clean_surface.parquet` + `rates.parquet`  *(owner: __)*
- [ ] **S1d** — Unit tests: cleaned-surface shape/integrity  *(owner: __)*

### Slice 2 — CRSP + realized returns

Independent of Slice 1; the link table lives here.

- [ ] **S2a** — Pull CRSP monthly v2 (adjust template's `pull_CRSP_stock.py`; delisting returns auto-integrate)  *(owner: __)*
- [ ] **S2b** — Pull S&P 500 constituents (`crsp.msp500list`) + CRSP–OptionMetrics link table (`wrdsapps_link_crsp_optionm`)  *(owner: __)*
- [ ] **S2c** — Build realized-returns table (apply the link, `secid ↔ permno`) → write `realized_returns.parquet`  *(owner: __)*
- [ ] **S2d** — Unit tests: the realized-returns join  *(owner: __)*

---

### Analysis tasks (small standalone units; chain A1 → A5)

Each reads a defined input and returns/writes a defined output.

- [ ] **A1** — Risk-neutral CDF (Breeden–Litzenberger). In: `clean_surface` + `rates`. Out: `surface → risk-neutral CDF` per (date, secid, horizon). Test: CDF monotonic, in [0,1].  *(owner: __)*
- [ ] **A2** — Risk-neutral crash probability. In: A1's CDF. Out: `prob_riskneutral` (integrate CDF below each `threshold`). Test: hand-checked value on one synthetic CDF.  *(owner: __)*
- [ ] **A3** — Fear correction (R_m², γ=2). In: A2 + market return. Out: corrected probability weighting. Test: correction moves mass *out* of the crash tail (prob drops vs. A2).  *(owner: __)*
- [ ] **A4** — Copula bounds. In: corrected probabilities. Out: `bound_lower`, `prob_star`, `bound_upper` (Fréchet–Hoeffding). Test: `bound_lower ≤ prob_star ≤ bound_upper` always.  *(owner: __)*
- [ ] **A5** — Pipeline orchestration → results table. In: A1–A4 wired over all dates/secids. Out: `results.parquet`. Test: schema + no NaNs in required columns.  *(owner: __)*

### Exhibit tasks (each is one table or one figure; independent, claim in any order)

All read `results.parquet` (+ `realized_returns.parquet` where noted).

- [ ] **E1** — Table 1: summary statistics *(replication)*  *(owner: __)*
- [ ] **E2** — Table 2: calibration regressions *(replication; slopes ≈ 1 / 0.7 / 0.5; needs `realized_returns`)*  *(owner: __)*
- [ ] **E3** — Figure 1 *(replication)*  *(owner: __)*
- [ ] **E4** — Figure 2 *(replication)*  *(owner: __)*
- [ ] **E5** — Own summary table *(20-pt deliverable; describes cleaned data; motivating caption)*  *(owner: __)*
- [ ] **E6** — Own figure *(20-pt deliverable; motivating caption)*  *(owner: __)*
- [ ] **E7** — LaTeX report assembly (pulls E1–E6 into the single document)  *(owner: __)*

### Packaging & infrastructure (small, claimable separately)

- [ ] **P1** — `crashbounds` package skeleton (pyproject, install, entry point)  *(owner: __)*
- [ ] **P2** — Live WRDS fetch in the package (wraps Slice 1/2 pulls)  *(owner: __)*
- [ ] **P3** — Report-generation module (wraps E-series exhibits)  *(owner: __)*
- [ ] **I1** — `doit` end-to-end wiring  *(owner: __)*
- [ ] **I2** — `.env` / `.env.example` + `settings.py` + `requirements.txt`  *(owner: __)*

---

### Extensions

- [ ] **X1** — Sector ETF surfaces (XLF/XLK/XLE/KRE): new secids through the Slice 1 surface pipeline  *(owner: __)*
- [ ] **X2** — SVB / March 2023 case study: read results (KRE, SIVB) vs. realized; interpret idiosyncratic crash / pinned lower bound  *(owner: __)*
- [ ] **X3** — Date extension through ~Aug 2025: each slice extends its own date range, then both validate updated exhibits  *(owner: __)*

---

### Joint — both members

- Replication of Tables 1–2 and Figures 1–2 against the paper's period: built by the
  engine + exhibit tasks above, but **both review and must understand them cold** for
  the individually-graded oral defense.
- End-to-end `doit` automation, `.env` config, requirements, and keeping secrets and
  raw data out of git history.
- `crashbounds` packaging is integrative (engine + report-gen + pull code) — good
  shared surface for the "both understand the whole project" defense requirement.

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

