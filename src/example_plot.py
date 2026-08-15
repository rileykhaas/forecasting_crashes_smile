"""Placeholder figure (self-contained template).

Emits a small PNG to OUTPUT_DIR so the example report scaffolding compiles
end-to-end under ``doit``. It uses synthetic data and has no external
dependencies; the real figures (#33 / E6) will replace it.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt

from settings import config

OUTPUT_DIR = Path(config("OUTPUT_DIR"))

sns.set()

np.random.seed(100)
idx = pd.date_range("2000-01-31", periods=120, freq="ME")
df = pd.DataFrame(
    {
        "Series A": np.random.normal(0.0, 1.0, 120).cumsum(),
        "Series B": np.random.normal(0.0, 1.0, 120).cumsum(),
    },
    index=idx,
)
df.plot()
plt.title("Placeholder example figure")
plt.ylabel("Synthetic level")
plt.savefig(OUTPUT_DIR / "example_plot.png")
