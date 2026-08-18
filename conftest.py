"""Pytest configuration.

Jupytext notebook sources (``*.ipynb.py``) are not importable modules --- their
names start with a digit (e.g. ``01_data_tour``) and they are meant to be converted
to notebooks, not imported. Exclude them from collection so ``pytest
--doctest-modules`` does not try to import them.
"""

collect_ignore_glob = ["*.ipynb.py"]
