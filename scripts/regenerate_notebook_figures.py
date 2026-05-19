"""Regenerate figures by executing code cells in selected notebooks.

This is a lightweight fallback for environments where nbconvert/nbclient is
not installed. It executes code cells in order and relies on each notebook's
existing save_figure(...) calls to refresh outputs/figures.
"""

import json
from pathlib import Path


NOTEBOOKS = [
    "notebooks/02_cancellation_demand_analysis.ipynb",
    "notebooks/03_customer_channel_analysis.ipynb",
    "notebooks/04_price_revenue_analysis.ipynb",
    "notebooks/05_stay_leadtime_behavior_analysis.ipynb",
]


def execute_notebook_code_cells(notebook_path):
    print(f"=== executing {notebook_path} ===")
    namespace = {"__name__": "__main__"}
    notebook = json.loads(Path(notebook_path).read_text(encoding="utf-8-sig"))

    for index, cell in enumerate(notebook["cells"], 1):
        if cell.get("cell_type") != "code":
            continue

        source = "".join(cell.get("source", []))
        if not source.strip():
            continue

        exec(compile(source, f"{notebook_path}:cell-{index}", "exec"), namespace)

    print(f"=== done {notebook_path} ===")


def main():
    for notebook_path in NOTEBOOKS:
        execute_notebook_code_cells(notebook_path)


if __name__ == "__main__":
    main()
