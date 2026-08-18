"""Run or update the project. This file uses the `doit` Python package. It works
like a Makefile, but is Python-based

"""

#######################################
## Configuration and Helpers for PyDoit
#######################################
## Make sure the src folder is in the path
import sys

sys.path.insert(1, "./src/")

import shutil
from os import environ
from pathlib import Path

from settings import config

DOIT_CONFIG = {"backend": "sqlite3", "dep_file": "./.doit-db.sqlite"}


BASE_DIR = config("BASE_DIR")
DATA_DIR = config("DATA_DIR")
MANUAL_DATA_DIR = config("MANUAL_DATA_DIR")
OUTPUT_DIR = config("OUTPUT_DIR")
OS_TYPE = config("OS_TYPE")

## Helpers for handling Jupyter Notebook tasks
environ["PYDEVD_DISABLE_FILE_VALIDATION"] = "1"


# fmt: off
## Helper functions for automatic execution of Jupyter notebooks
def jupyter_execute_notebook(notebook_path):
    return f"jupyter nbconvert --execute --to notebook --ClearMetadataPreprocessor.enabled=True --inplace {notebook_path}"
def jupyter_to_html(notebook_path, output_dir=OUTPUT_DIR):
    return f"jupyter nbconvert --to html --output-dir={output_dir} {notebook_path}"
def jupyter_to_md(notebook_path, output_dir=OUTPUT_DIR):
    """Requires jupytext"""
    return f"jupytext --to markdown --output-dir={output_dir} {notebook_path}"
def jupyter_clear_output(notebook_path):
    """Clear the output of a notebook"""
    return f"jupyter nbconvert --ClearOutputPreprocessor.enabled=True --ClearMetadataPreprocessor.enabled=True --inplace {notebook_path}"
# fmt: on


def mv(from_path, to_path):
    """Move a file to a folder"""
    from_path = Path(from_path)
    to_path = Path(to_path)
    to_path.mkdir(parents=True, exist_ok=True)
    if OS_TYPE == "nix":
        command = f"mv {from_path} {to_path}"
    else:
        command = f"move {from_path} {to_path}"
    return command


def copy_file(origin_path, destination_path, mkdir=True):
    """Create a Python action for copying a file."""

    def _copy_file():
        origin = Path(origin_path)
        dest = Path(destination_path)
        if mkdir:
            dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origin, dest)

    return _copy_file


##################################
## Begin rest of PyDoit tasks here
##################################


def task_config():
    """Create empty directories for data and output if they don't exist"""
    return {
        "actions": ["python ./src/settings.py"],
        "targets": [DATA_DIR, OUTPUT_DIR],
        "file_dep": ["./src/settings.py"],
        "clean": [],
    }


def task_pull_crsp_stock():
    """Pull the CRSP monthly stock panel from WRDS.

    Also force-includes the extension sector-ETF permnos (#34), which are not
    ``securitytype='EQTY'``; their secids come from the OptionMetrics pull manifest
    and map to permnos via the CRSP-OptionMetrics link, so this pull now depends on
    those two artifacts.
    """
    return {
        "actions": [
            "python ./src/settings.py",
            "python ./src/pull_CRSP_stock.py",
        ],
        "targets": [DATA_DIR / "CRSP_monthly_stock.parquet"],
        "file_dep": [
            "./src/settings.py",
            "./src/pull_CRSP_stock.py",
            DATA_DIR / "crsp_optionm_link.parquet",
            DATA_DIR / "optionm_pull_secids.parquet",
        ],
        "clean": [],
    }


def task_pull_sp500_constituents():
    """Pull S&P 500 constituent membership (crsp.msp500list) from WRDS."""
    return {
        "actions": [
            "python ./src/settings.py",
            "python ./src/pull_sp500.py",
        ],
        "targets": [DATA_DIR / "sp500_constituents.parquet"],
        "file_dep": ["./src/settings.py", "./src/pull_sp500.py"],
        "clean": [],
    }


def task_pull_crsp_optionm_link():
    """Pull the CRSP-OptionMetrics link table (opcrsphist) from WRDS."""
    return {
        "actions": [
            "python ./src/settings.py",
            "python ./src/pull_link.py",
        ],
        "targets": [DATA_DIR / "crsp_optionm_link.parquet"],
        "file_dep": ["./src/settings.py", "./src/pull_link.py"],
        "clean": [],
    }


def task_pull_optionmetrics():
    """Pull OptionMetrics surface/rates/security files for the secid universe + ETFs."""
    return {
        "actions": [
            "python ./src/settings.py",
            "python ./src/pull_optionmetrics.py",
        ],
        "targets": [
            DATA_DIR / "optionm_vol_surface.parquet",
            DATA_DIR / "optionm_zero_curve.parquet",
            DATA_DIR / "optionm_security_names.parquet",
            DATA_DIR / "optionm_pull_secids.parquet",
        ],
        "file_dep": [
            "./src/settings.py",
            "./src/pull_optionmetrics.py",
            "./src/sp500_secid_universe.py",
            "./src/schema.py",
            DATA_DIR / "sp500_secid_universe.parquet",
        ],
        "clean": [],
    }


def task_build_secid_universe():
    """Build the month-end S&P 500 constituent secid universe (Slice 2).

    Expands index membership onto the last NYSE trading day of each month and
    attaches the best-score OptionMetrics secid. Depends on the two Slice-2
    pulls (sp500_constituents, crsp_optionm_link).
    """
    return {
        "actions": ["python ./src/sp500_secid_universe.py"],
        "targets": [DATA_DIR / "sp500_secid_universe.parquet"],
        "file_dep": [
            "./src/sp500_secid_universe.py",
            "./src/pull_sp500.py",
            "./src/pull_link.py",
            DATA_DIR / "sp500_constituents.parquet",
            DATA_DIR / "crsp_optionm_link.parquet",
        ],
        "clean": [],
    }


def task_build_realized_returns():
    """Build CRSP forward realized gross returns, keyed by secid (Slice 2).

    Computes gross forward returns for each horizon in schema.HORIZONS_MONTHS
    from the CRSP monthly file (delisting returns folded into mthret), and
    attaches the OptionMetrics secid via the CRSP-OptionMetrics link. The S&P 500
    index itself is added from the CRSP index file (msix) under SPX_SECID, so its
    i = m crash bound has a realized outcome. Depends on the CRSP stock and index
    pulls and the link table pull.
    """
    return {
        "actions": ["python ./src/realized_returns.py"],
        "targets": [DATA_DIR / "realized_returns.parquet"],
        "file_dep": [
            "./src/realized_returns.py",
            "./src/pull_CRSP_stock.py",
            "./src/pull_link.py",
            "./src/pull_optionmetrics.py",
            "./src/schema.py",
            DATA_DIR / "CRSP_monthly_stock.parquet",
            DATA_DIR / "CRSP_MSIX.parquet",
            DATA_DIR / "crsp_optionm_link.parquet",
            DATA_DIR / "optionm_pull_secids.parquet",
        ],
        "clean": [],
    }


def task_clean_rates():
    """Clean the OptionMetrics zero curve into rates.parquet (Slice 1)."""
    return {
        "actions": ["python ./src/rates.py"],
        "targets": [DATA_DIR / "rates.parquet"],
        "file_dep": [
            "./src/rates.py",
            "./src/schema.py",
            DATA_DIR / "optionm_zero_curve.parquet",
        ],
        "clean": [],
    }


def task_clean_surface():
    """Filter the OptionMetrics surface into clean_surface.parquet (Slice 1).

    Applies the paper's Appendix-D filters and attaches CRSP spot (constituents
    via the #14 link, the S&P 500 index via spindx, and the extension sector ETFs
    via their own permno, #34).
    """
    return {
        "actions": ["python ./src/clean_surface.py"],
        "targets": [DATA_DIR / "clean_surface.parquet"],
        "file_dep": [
            "./src/clean_surface.py",
            "./src/schema.py",
            "./src/sp500_secid_universe.py",
            "./src/pull_link.py",
            "./src/pull_optionmetrics.py",
            DATA_DIR / "optionm_vol_surface.parquet",
            DATA_DIR / "sp500_secid_universe.parquet",
            DATA_DIR / "CRSP_monthly_stock.parquet",
            DATA_DIR / "CRSP_MSIX.parquet",
            DATA_DIR / "crsp_optionm_link.parquet",
            DATA_DIR / "optionm_pull_secids.parquet",
        ],
        "clean": [],
    }


def task_pipeline():
    """Run A1-A5 end to end into results.parquet (Appendix D bounds).

    Combines clean_surface + rates (Slice 1) with realized_returns (Slice 2)
    through the engine (rnd.py, utility_correction.py, bounds.py) to produce
    the P^L / P* / P^U + realized-outcome table every figure/table reads from.
    """
    return {
        "actions": ["python ./src/run_pipeline.py"],
        "targets": [OUTPUT_DIR / "results.parquet"],
        "file_dep": [
            "./src/run_pipeline.py",
            "./src/rnd.py",
            "./src/utility_correction.py",
            "./src/bounds.py",
            "./src/schema.py",
            DATA_DIR / "clean_surface.parquet",
            DATA_DIR / "rates.parquet",
            DATA_DIR / "realized_returns.parquet",
        ],
        "clean": [],
    }


def task_table1():
    """E1: Replicate Table 1 (summary statistics) over the 1996-2022 window."""
    return {
        "actions": ["python ./src/exhibit_table1.py"],
        "targets": [
            OUTPUT_DIR / "table1.tex", OUTPUT_DIR / "table1.csv",
            OUTPUT_DIR / "table1_ext.tex", OUTPUT_DIR / "table1_ext.csv",
        ],
        "file_dep": [
            "./src/exhibit_table1.py",
            "./src/sp500_secid_universe.py",
            "./src/schema.py",
            OUTPUT_DIR / "results.parquet",
            DATA_DIR / "sp500_secid_universe.parquet",
        ],
        "clean": True,
    }


def task_fig1():
    """E: Figure 1 -- single-name crash-probability bounds (AAPL & AIG)."""
    return {
        "actions": ["python ./src/exhibit_fig1.py"],
        "targets": [
            OUTPUT_DIR / "fig1_single_name_bounds.png",
            OUTPUT_DIR / "fig1_single_name_bounds_ext.png",
        ],
        "file_dep": [
            "./src/exhibit_fig1.py",
            "./src/plot_style.py",
            OUTPUT_DIR / "results.parquet",
        ],
        "clean": True,
    }


def task_fig2():
    """E: Figure 2 -- cross-sectional median bounds + the S&P 500 index."""
    return {
        "actions": ["python ./src/exhibit_fig2.py"],
        "targets": [
            OUTPUT_DIR / "fig2_median_bounds_market.png",
            OUTPUT_DIR / "fig2_median_bounds_market_ext.png",
        ],
        "file_dep": [
            "./src/exhibit_fig2.py",
            "./src/plot_style.py",
            "./src/sp500_secid_universe.py",
            OUTPUT_DIR / "results.parquet",
            DATA_DIR / "sp500_secid_universe.parquet",
        ],
        "clean": True,
    }


def task_fig6():
    """E: Figure 6 -- out-of-sample R^2s of the lower bound vs. the risk-neutral."""
    return {
        "actions": ["python ./src/exhibit_fig6.py"],
        "targets": [
            OUTPUT_DIR / "fig6_oos_r2.png",
            OUTPUT_DIR / "fig6_oos_r2_ext.png",
        ],
        "file_dep": [
            "./src/exhibit_fig6.py",
            "./src/sp500_secid_universe.py",
            OUTPUT_DIR / "results.parquet",
            DATA_DIR / "sp500_secid_universe.parquet",
        ],
        "clean": True,
    }


def task_table2():
    """E: Replicate Table 2 -- regression calibration tests (alpha, beta, R^2)."""
    return {
        "actions": ["python ./src/exhibit_table2.py"],
        "targets": [
            OUTPUT_DIR / "table2.tex", OUTPUT_DIR / "table2.csv",
            OUTPUT_DIR / "table2_ext.tex", OUTPUT_DIR / "table2_ext.csv",
        ],
        "file_dep": [
            "./src/exhibit_table2.py",
            "./src/sp500_secid_universe.py",
            "./src/schema.py",
            OUTPUT_DIR / "results.parquet",
            DATA_DIR / "sp500_secid_universe.parquet",
        ],
        "clean": True,
    }


def task_eda():
    """E: EDA of the underlying option/return panel -- coverage table + 2x2 figure."""
    return {
        "actions": ["python ./src/exhibit_eda.py"],
        "targets": [
            OUTPUT_DIR / "eda_coverage.tex", OUTPUT_DIR / "eda_coverage.csv",
            OUTPUT_DIR / "eda_coverage_ext.tex", OUTPUT_DIR / "eda_coverage_ext.csv",
            OUTPUT_DIR / "eda_panel.png", OUTPUT_DIR / "eda_panel_ext.png",
        ],
        "file_dep": [
            "./src/exhibit_eda.py",
            "./src/clean_surface.py",
            "./src/realized_returns.py",
            "./src/sp500_secid_universe.py",
            DATA_DIR / "clean_surface.parquet",
            DATA_DIR / "realized_returns.parquet",
            DATA_DIR / "sp500_secid_universe.parquet",
        ],
        "clean": True,
    }


def task_etf_bounds():
    """X: Sector-ETF crash-probability bounds vs. the S&P 500 (extension #34)."""
    return {
        "actions": ["python ./src/exhibit_etf_bounds.py"],
        "targets": [
            OUTPUT_DIR / "etf_bounds.tex", OUTPUT_DIR / "etf_bounds.csv",
            OUTPUT_DIR / "etf_bounds_ext.tex", OUTPUT_DIR / "etf_bounds_ext.csv",
            OUTPUT_DIR / "fig_etf_sector_bounds.png",
            OUTPUT_DIR / "fig_etf_sector_bounds_ext.png",
        ],
        "file_dep": [
            "./src/exhibit_etf_bounds.py",
            "./src/schema.py",
            OUTPUT_DIR / "results.parquet",
            DATA_DIR / "optionm_pull_secids.parquet",
        ],
        "clean": True,
    }


def task_industry_compare():
    """X: Industry proxy (avg. of constituents) vs. direct sector-ETF bound (#34)."""
    return {
        "actions": ["python ./src/exhibit_industry_compare.py"],
        "targets": [
            OUTPUT_DIR / "industry_tightness.tex", OUTPUT_DIR / "industry_tightness.csv",
            OUTPUT_DIR / "industry_tightness_ext.tex", OUTPUT_DIR / "industry_tightness_ext.csv",
            OUTPUT_DIR / "fig_industry_compare.png",
            OUTPUT_DIR / "fig_industry_compare_ext.png",
        ],
        "file_dep": [
            "./src/exhibit_industry_compare.py",
            "./src/ff_industry.py",
            "./src/exhibit_etf_bounds.py",
            "./src/sp500_secid_universe.py",
            "./src/pull_CRSP_stock.py",
            "./src/schema.py",
            OUTPUT_DIR / "results.parquet",
            DATA_DIR / "sp500_secid_universe.parquet",
            DATA_DIR / "CRSP_monthly_stock.parquet",
            DATA_DIR / "optionm_pull_secids.parquet",
        ],
        "clean": True,
    }


def task_pull_svb_daily():
    """Pull daily OptionMetrics data for the SVB case study (#31): SIVB/KRE/XLF/SPX,
    Feb-Mar 2023 (surface + spot + zero curve). A small self-contained daily slice."""
    return {
        "actions": [
            "python ./src/settings.py",
            "python ./src/pull_svb_daily.py",
        ],
        "targets": [
            DATA_DIR / "svb_daily_surface.parquet",
            DATA_DIR / "svb_daily_spot.parquet",
            DATA_DIR / "svb_daily_zero.parquet",
        ],
        "file_dep": ["./src/settings.py", "./src/pull_svb_daily.py", "./src/schema.py"],
        "clean": [],
    }


def task_svb_case_study():
    """X: SVB case study -- daily crash bounds for SIVB/KRE/XLF through the crisis (#31)."""
    return {
        "actions": ["python ./src/exhibit_svb.py"],
        "targets": [
            OUTPUT_DIR / "svb_daily_bounds.parquet",
            OUTPUT_DIR / "fig_svb_case_study.png",
            OUTPUT_DIR / "svb_realized.tex",
            OUTPUT_DIR / "svb_realized.csv",
        ],
        "file_dep": [
            "./src/exhibit_svb.py",
            "./src/pull_svb_daily.py",
            "./src/rates.py",
            "./src/run_pipeline.py",
            "./src/rnd.py",
            "./src/bounds.py",
            "./src/utility_correction.py",
            "./src/schema.py",
            DATA_DIR / "svb_daily_surface.parquet",
            DATA_DIR / "svb_daily_spot.parquet",
            DATA_DIR / "svb_daily_zero.parquet",
        ],
        "clean": True,
    }


notebook_tasks = {
    "01_data_tour.ipynb.py": {
        "path": "./src/01_data_tour.ipynb.py",
        "file_dep": [
            DATA_DIR / "clean_surface.parquet",
            OUTPUT_DIR / "results.parquet",
        ],
        "targets": [],
    },
}


# fmt: off
def task_run_notebooks():
    """Preps the notebooks for presentation format.
    Execute notebooks if the script version of it has been changed.
    """
    for notebook in notebook_tasks.keys():
        pyfile_path = Path(notebook_tasks[notebook]["path"])
        notebook_path = pyfile_path.with_suffix("")  # strips .py, leaves .ipynb
        notebook_name = notebook_path.stem  # e.g. "01_example_notebook_interactive"
        yield {
            "name": notebook,
            "actions": [
                """python -c "import sys; from datetime import datetime; print(f'Start """ + notebook + """: {datetime.now()}', file=sys.stderr)" """,
                f"jupytext --to notebook --output {notebook_path} {pyfile_path}",
                jupyter_execute_notebook(notebook_path),
                jupyter_to_html(notebook_path),
                mv(notebook_path, OUTPUT_DIR),
                """python -c "import sys; from datetime import datetime; print(f'End """ + notebook + """: {datetime.now()}', file=sys.stderr)" """,
            ],
            "file_dep": [
                pyfile_path,
                *notebook_tasks[notebook]["file_dep"],
            ],
            "targets": [
                OUTPUT_DIR / f"{notebook_name}.html",
                *notebook_tasks[notebook]["targets"],
            ],
            "clean": True,
        }
# fmt: on

###############################################################
## Task below is for LaTeX compilation
###############################################################


def task_compile_latex_docs():
    """Compile the project report (report.tex) to PDF.

    The report \\input's the auto-generated exhibits from OUTPUT_DIR, so those
    are file_deps -- doit builds them first and rebuilds the PDF when they change.
    """
    return {
        "actions": [
            "latexmk -xelatex -halt-on-error -cd ./reports/report.tex",  # Compile
            "latexmk -xelatex -halt-on-error -c -cd ./reports/report.tex",  # Clean aux
        ],
        "targets": ["./reports/report.pdf"],
        "file_dep": [
            "./reports/report.tex",
            "./reports/my_article_header.sty",
            "./reports/my_common_header.sty",
            OUTPUT_DIR / "table1.tex",
            OUTPUT_DIR / "table2.tex",
            OUTPUT_DIR / "table1_ext.tex",
            OUTPUT_DIR / "table2_ext.tex",
            OUTPUT_DIR / "fig1_single_name_bounds.png",
            OUTPUT_DIR / "fig2_median_bounds_market.png",
            OUTPUT_DIR / "fig1_single_name_bounds_ext.png",
            OUTPUT_DIR / "fig2_median_bounds_market_ext.png",
            OUTPUT_DIR / "fig6_oos_r2.png",
            OUTPUT_DIR / "fig6_oos_r2_ext.png",
            OUTPUT_DIR / "eda_coverage.tex",
            OUTPUT_DIR / "eda_panel.png",
            OUTPUT_DIR / "etf_bounds.tex",
            OUTPUT_DIR / "fig_etf_sector_bounds.png",
            OUTPUT_DIR / "industry_tightness.tex",
            OUTPUT_DIR / "fig_industry_compare.png",
            OUTPUT_DIR / "fig_svb_case_study.png",
            OUTPUT_DIR / "svb_realized.tex",
        ],
        "clean": True,
    }


sphinx_targets = [
    "./docs/index.html",
]


def task_build_chartbook_site():
    """Compile Sphinx Docs"""
    notebook_scripts = [
        Path(notebook_tasks[notebook]["path"]) for notebook in notebook_tasks.keys()
    ]
    file_dep = [
        "./README.md",
        "./chartbook.toml",
        *notebook_scripts,
    ]

    return {
        "actions": [
            # --size-threshold 2000 (MB) so the large surface parquets still get
            # a data glimpse (date range etc.) instead of "N/A (large file)".
            "chartbook build -f --size-threshold 2000",
        ],  # Use docs as build destination
        "targets": sphinx_targets,
        "file_dep": file_dep,
        "task_dep": [
            "run_notebooks",
        ],
        "clean": True,
    }


def task_run_pytest():
    """Run pytest and save results to OUTPUT_DIR"""
    src_py_files = list(Path("./src").glob("*.py"))
    test_output = OUTPUT_DIR / "pytest_results.xml"

    def run_pytest():
        import subprocess

        result = subprocess.run(
            ["pytest", f"--junitxml={test_output}"],
        )
        if result.returncode != 0:
            # Remove the XML so doit won't consider the target up-to-date
            Path(test_output).unlink(missing_ok=True)
            raise RuntimeError(f"pytest failed with exit code {result.returncode}")

    return {
        "actions": [run_pytest],
        "targets": [test_output],
        "file_dep": src_py_files,
        "clean": True,
        "verbosity": 2,
    }
