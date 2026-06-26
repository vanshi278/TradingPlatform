"""Model interpretability — SHAP feature attribution, with a graceful fallback to
the model's built-in feature_importances_ if SHAP can't run."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ml.features import FEATURE_COLUMNS

RESULTS = Path(__file__).resolve().parents[2] / "results"


def feature_importance(model, X: pd.DataFrame) -> pd.Series:
    """Mean |SHAP value| per feature (preferred), else feature_importances_."""
    try:
        import shap

        sv = shap.TreeExplainer(model).shap_values(X)
        imp = np.abs(np.asarray(sv)).mean(axis=0)
        return pd.Series(imp, index=FEATURE_COLUMNS, name="mean_abs_shap").sort_values(ascending=False)
    except Exception:
        imp = getattr(model, "feature_importances_", None)
        if imp is None:
            return pd.Series(dtype=float)
        return pd.Series(imp, index=FEATURE_COLUMNS, name="importance").sort_values(ascending=False)


def save_shap_summary(model, X: pd.DataFrame, path: Path | None = None) -> str:
    path = Path(path) if path else RESULTS / "shap_summary.png"
    RESULTS.mkdir(exist_ok=True)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import shap

        sv = shap.TreeExplainer(model).shap_values(X)
        shap.summary_plot(sv, X, show=False, plot_type="bar")
        plt.tight_layout()
        plt.savefig(path, dpi=110)
        plt.close()
        return str(path)
    except Exception as exc:  # noqa: BLE001 - fall back to a plain importance bar
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            imp = feature_importance(model, X)
            imp.sort_values().plot.barh(figsize=(8, 6))
            plt.title("feature importance")
            plt.tight_layout()
            plt.savefig(path, dpi=110)
            plt.close()
            return f"{path} (feature_importances_ fallback: {exc})"
        except Exception as exc2:  # noqa: BLE001
            return f"(interpretability plot skipped: {exc2})"
