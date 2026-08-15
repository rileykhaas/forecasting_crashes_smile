"""Placeholder summary-statistics table (self-contained template).

Emits a small LaTeX summary-stats table to OUTPUT_DIR so the example report
scaffolding compiles end-to-end under ``doit``. It uses synthetic data and has
no external dependencies; the real summary-statistics exhibit (the EDA product,
#33) will replace it.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from settings import config

OUTPUT_DIR = Path(config("OUTPUT_DIR"))


def float_format_func(x):
    return "{:.2f}".format(x)


np.random.seed(100)

# Synthetic stand-ins for the real panel's summary columns.
df = pd.DataFrame(
    {
        "Inflation": np.random.normal(3.0, 1.5, 300),
        "Real GDP": np.random.normal(2.5, 2.0, 300),
    }
)
describe = df.describe().T.rename(
    columns={"25%": "25\\%", "50%": "50\\%", "75%": "75\\%"}
)
describe["count"] = describe["count"].astype(int)
describe.columns.name = "Placeholder summary statistics"
latex_table_string = describe.to_latex(escape=False, float_format=float_format_func)

path = OUTPUT_DIR / "example_table.tex"
with open(path, "w") as text_file:
    text_file.write(latex_table_string)
