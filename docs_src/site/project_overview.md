# Project Overview

## forecasting_crashes_smile

This project replicates and extends Martin & Shi (2025), *"Forecasting Crashes with a
Smile."* The paper reads the option-implied volatility smile to estimate the *physical*
probability that a stock or the market crashes over the next 1–12 months. From raw WRDS
option and return data we rebuild the paper's option-implied **lower bound**, a
fear-corrected, model-free crash forecast, reproduce its tables and figures over
1996–2022 under unit tests, and carry every exhibit through 2025. Beyond the
replication we add our own exploratory analysis of the panel and three extensions:
direct sector-ETF crash bounds, a proxy-vs-direct industry comparison, and a daily case
study of the March-2023 Silicon Valley Bank collapse.

| Section | Description |
|---------|-------------|
| Goals | Project objectives and success criteria |
| Data Sources | Description of datasets and how they are obtained |
| Methodology | Approach, methods, and implementation details |

```{toctree}
:maxdepth: 1
:caption: Project Details

project_overview/goals
project_overview/data_sources
project_overview/methodology
```
