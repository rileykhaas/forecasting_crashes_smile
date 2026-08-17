"""Shared matplotlib styling so the replicated figures match the paper's look.

The paper's exhibits are ggplot charts: biennial year ticks, data flush to the
left/right edges, 0% floating just off the x-axis, a faint grey grid behind the
data, and no box spines. ``paper_style`` applies all of that to an axis so every
figure (1, 2, 6, ...) is visually consistent.
"""

import matplotlib.dates as mdates
from matplotlib.ticker import MultipleLocator, PercentFormatter


def paper_style(ax, ymax, y_floor=0.62, y_minor=0.05):
    """Apply the paper's figure axis styling to ``ax``.

    Parameters
    ----------
    ax : matplotlib Axes
    ymax : float
        The largest plotted value; the y-axis top is ``max(y_floor, ymax*1.05)``
        so it always reaches ``y_floor`` but never clips the data.
    y_floor : float
        Minimum y-axis top (the paper's axis, e.g. 0.62 for a 60% axis).
    y_minor : float
        Minor y grid step (e.g. 0.05 on a 60% axis, 0.025 on a 25% axis).
    """
    ax.margins(x=0)  # data flush to the left/right edges
    ax.set_ylim(-0.012, max(y_floor, ymax * 1.05))  # 0% floats just off the axis
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=1.0))
    # Biennial year ticks (1998, 2000, ...), yearly minor.
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_minor_locator(mdates.YearLocator(1))
    ax.yaxis.set_minor_locator(MultipleLocator(y_minor))
    # Faint ggplot-style grid behind the data, inside a thin outer border box.
    ax.grid(True, which="major", color="#d0d0d0", linewidth=0.6)
    ax.grid(True, which="minor", color="#ececec", linewidth=0.4)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_edgecolor("#333333")
        spine.set_linewidth(0.8)
    ax.set_xlabel("Date")
