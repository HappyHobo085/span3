"""Lei die Saamry aankomstyd-model op (minute wat iemand voor sy eerste klas aankom).

Twee databronne, albei opsioneel:
- ml_data/werklik_selfgerapporteer.csv (selfgerapporteerde opname), en
- met --van-logs: onlangse KAMPUSHEK-skanderings uit die databasis
  (sien scripts/aankoms_data_uit_logs.py).

Die keuseregel is dieselfde vir albei: kluster-mediaan moet die globale
mediaan met minstens 1 SE klop, en die ML-model moet die beste eenvoudige reël
met minstens 1 SE klop. Die nuwe model vervang die bestaande een eers nadat dit
suksesvol gelaai en getoets is; met te min data bly die bestaande model staan.
"""

import argparse
import sys
import os
import numpy as np
import pandas as pd
import joblib
import sklearn
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import GroupKFold, KFold
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OrdinalEncoder
from sklearn.pipeline import Pipeline

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from services.compatibiliteit_service import _vind_kluster

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "ml_data", "werklik_selfgerapporteer.csv")
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "ml_models", "aankoms_model.joblib")

# Minimum data voordat 'n nuwe model die bestaande een mag vervang.
MIN_RYE = int(os.getenv("SAAMRY_MIN_RYE", "40"))
MIN_GROEPE = int(os.getenv("SAAMRY_MIN_PERSONE", "10"))


def berei_voor(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Preprocess role
    df["rol"] = df["rol"].astype(str).str.upper().replace("ALBEI", "BEIDE")

    # Preprocess kluster: dieselfde opsoek as wat die voorspelling gebruik
    df["kluster"] = df["voorstad"].apply(
        lambda x: (_vind_kluster(str(x)) if isinstance(x, str) and x.strip() else None) or "onbekend"
    )

    # Ensure is_koshuis is numeric
    if "is_koshuis" in df.columns:
        df["is_koshuis"] = df["is_koshuis"].astype(int)
    else:
        df["is_koshuis"] = 0

    df["klas_begin_minuut"] = df["klas_begin_minuut"].astype(int)
    df["vroeg"] = (df["klas_begin_minuut"] <= 480).astype(int)
    return df.reset_index(drop=True)


def _voue(X, groepe):
    """Kruisvalidasie-voue.

    Sonder groepe: 5x herhaalde 10-voudige KFold (soos die oorspronklike opname).
    Met groepe (een persoon het verskeie rye in die logs): GroupKFold, sodat
    dieselfde persoon nooit in beide oplei- en toetsdeel is nie.
    """
    if groepe is None:
        for rep in range(5):
            kf = KFold(n_splits=10, shuffle=True, random_state=rep)
            for train_idx, test_idx in kf.split(X):
                yield rep, train_idx, test_idx
        return
    n = min(10, len(np.unique(groepe)))
    for train_idx, test_idx in GroupKFold(n_splits=n).split(X, groups=groepe):
        yield 0, train_idx, test_idx


def kies_en_bou_model(df: pd.DataFrame, groepe=None) -> dict:
    target = "offset_tipies"
    y = df[target].values

    features = ["klas_begin_minuut", "kluster", "rol", "is_koshuis"]
    X = df[features].copy()

    # Define baselines
    N = len(df)
    REPS = 5 if groepe is None else 1

    # 2. Globale Mediaan
    global_median = np.median(y)

    # 3. Kluster-Mediaan (with CV-like behavior, but since it's a simple lookup, we compute out-of-fold predictions)
    # We will do a 5x10 K-Fold CV to compute OOF predictions for all models

    oof_15 = np.zeros((REPS, N))
    oof_global = np.zeros((REPS, N))
    oof_cluster = np.zeros((REPS, N))
    oof_ml_50 = np.zeros((REPS, N))
    oof_ml_10 = np.zeros((REPS, N))
    oof_ml_90 = np.zeros((REPS, N))

    np.random.seed(42)

    categorical_features = ["kluster", "rol"]
    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1), categorical_features)
        ],
        remainder="passthrough"
    )

    model_50 = Pipeline([
        ("pre", preprocessor),
        ("gbm", HistGradientBoostingRegressor(loss="quantile", quantile=0.5, max_depth=3, min_samples_leaf=10, random_state=42))
    ])
    model_10 = Pipeline([
        ("pre", preprocessor),
        ("gbm", HistGradientBoostingRegressor(loss="quantile", quantile=0.1, max_depth=3, min_samples_leaf=10, random_state=42))
    ])
    model_90 = Pipeline([
        ("pre", preprocessor),
        ("gbm", HistGradientBoostingRegressor(loss="quantile", quantile=0.9, max_depth=3, min_samples_leaf=10, random_state=42))
    ])

    for rep, train_idx, test_idx in _voue(X, groepe):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train = y[train_idx]

        # 1. Constant 15
        oof_15[rep, test_idx] = 15.0

        # 2. Global median
        g_med = np.median(y_train)
        oof_global[rep, test_idx] = g_med

        # 3. Cluster median
        df_train = df.iloc[train_idx]
        # Calculate counts
        group_counts = df_train.groupby(["kluster", "vroeg"]).size()
        cluster_counts = df_train.groupby("kluster").size()

        group_medians = df_train.groupby(["kluster", "vroeg"])[target].median()
        cluster_medians = df_train.groupby("kluster")[target].median()

        for i, idx in enumerate(test_idx):
            k = X_test["kluster"].iloc[i]
            v = df["vroeg"].iloc[idx]
            if group_counts.get((k, v), 0) >= 8:
                oof_cluster[rep, idx] = group_medians.loc[(k, v)]
            elif cluster_counts.get(k, 0) >= 8:
                oof_cluster[rep, idx] = cluster_medians.loc[k]
            else:
                oof_cluster[rep, idx] = g_med

        # 4. ML
        model_50.fit(X_train, y_train)
        model_10.fit(X_train, y_train)
        model_90.fit(X_train, y_train)

        oof_ml_50[rep, test_idx] = model_50.predict(X_test)
        oof_ml_10[rep, test_idx] = model_10.predict(X_test)
        oof_ml_90[rep, test_idx] = model_90.predict(X_test)

    # Calculate average OOF error per row
    mae_15_row = np.abs(oof_15.mean(axis=0) - y)
    mae_global_row = np.abs(oof_global.mean(axis=0) - y)
    mae_cluster_row = np.abs(oof_cluster.mean(axis=0) - y)
    mae_ml_row = np.abs(oof_ml_50.mean(axis=0) - y)

    print(f"OOF MAE (15 min): {mae_15_row.mean():.2f}")
    print(f"OOF MAE (Global Median): {mae_global_row.mean():.2f}")
    print(f"OOF MAE (Cluster Median): {mae_cluster_row.mean():.2f}")
    print(f"OOF MAE (ML GBM): {mae_ml_row.mean():.2f}")

    # Paired Bootstrap
    def bootstrap_diff(err_a, err_b, n_boot=1000):
        diffs = err_a - err_b
        boot_means = []
        for _ in range(n_boot):
            boot_sample = np.random.choice(diffs, size=len(diffs), replace=True)
            boot_means.append(np.mean(boot_sample))
        return np.mean(boot_means), np.std(boot_means)

    # Selection Rule
    model_type = "MEDIAAN"

    # 1. Does Cluster beat Global by 1 SE?
    mean_diff_cg, se_cg = bootstrap_diff(mae_global_row, mae_cluster_row)
    if mean_diff_cg >= se_cg and mae_cluster_row.mean() < mae_global_row.mean():
        print(f"Cluster Median beats Global Median by {mean_diff_cg:.2f} (SE: {se_cg:.2f})")
        best_simple = "CLUSTER"
        mae_simple_row = mae_cluster_row
    else:
        print(f"Cluster Median DOES NOT beat Global Median by 1 SE (Diff: {mean_diff_cg:.2f}, SE: {se_cg:.2f})")
        best_simple = "GLOBAL"
        mae_simple_row = mae_global_row

    # 2. Does ML beat best_simple by 1 SE?
    mean_diff_ml, se_ml = bootstrap_diff(mae_simple_row, mae_ml_row)
    if mean_diff_ml >= se_ml and mae_ml_row.mean() < mae_simple_row.mean():
        print(f"ML GBM beats {best_simple} by {mean_diff_ml:.2f} (SE: {se_ml:.2f})")
        model_type = "ML"
    else:
        print(f"ML GBM DOES NOT beat {best_simple} by 1 SE (Diff: {mean_diff_ml:.2f}, SE: {se_ml:.2f})")
        model_type = best_simple

    print(f"Selected Model: {model_type}")

    # Build final model
    known_clusters = list(df["kluster"].unique())

    if model_type == "ML":
        model_50.fit(X, y)
        model_10.fit(X, y)
        model_90.fit(X, y)

        # OOF coverage
        mean_ml_10 = oof_ml_10.mean(axis=0)
        mean_ml_90 = oof_ml_90.mean(axis=0)
        coverage = np.mean((y >= mean_ml_10) & (y <= mean_ml_90))
        print(f"ML Coverage (10-90%): {coverage*100:.1f}%")

        final_model = {
            "type": "ML",
            "q50": model_50,
            "q10": model_10,
            "q90": model_90,
            "global_median": global_median,
            "known_clusters": known_clusters,
            "features": features,
            "sklearn_version": sklearn.__version__
        }
    else:
        # Train full median rules
        mad = np.median(np.abs(y - global_median))
        sigma = 1.4826 * mad
        sigma = min(max(sigma, 5.0), 30.0)

        group_medians = df.groupby(["kluster", "vroeg"])[target].median().to_dict()
        cluster_medians = df.groupby("kluster")[target].median().to_dict()
        group_counts = df.groupby(["kluster", "vroeg"]).size().to_dict()
        cluster_counts = df.groupby("kluster").size().to_dict()

        final_model = {
            "type": "MEDIAAN",
            "rule": model_type,  # "GLOBAL" or "CLUSTER"
            "global_median": global_median,
            "sigma": sigma,
            "group_medians": group_medians,
            "cluster_medians": cluster_medians,
            "group_counts": group_counts,
            "cluster_counts": cluster_counts,
            "known_clusters": known_clusters,
            "features": features,
            "sklearn_version": sklearn.__version__
        }
    return final_model


def stoor_veilig(final_model: dict, pad: str | None = None) -> None:
    """Skryf na 'n tydelike lêer, laai en toets dit, en vervang dan eers die bestaande model."""
    pad = pad or MODEL_PATH
    tmp = pad + ".nuut"
    joblib.dump(final_model, tmp)
    try:
        gelaai = joblib.load(tmp)
        if gelaai.get("type") == "ML":
            proef = pd.DataFrame([{"klas_begin_minuut": 480, "kluster": gelaai["known_clusters"][0],
                                   "rol": "BEIDE", "is_koshuis": 0}])
            for q in ("q10", "q50", "q90"):
                waarde = float(gelaai[q].predict(proef)[0])
                if not np.isfinite(waarde):
                    raise ValueError(f"{q} gee 'n ongeldige voorspelling")
        elif not np.isfinite(float(gelaai["global_median"])):
            raise ValueError("global_median is ongeldig")
        os.replace(tmp, pad)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def laai_data(van_logs: bool):
    """Gee (df, groepe) terug uit die selfgerapporteerde CSV en/of die heklogs."""
    dele = []
    if os.path.exists(DATA_PATH):
        csv = pd.read_csv(DATA_PATH)
        csv["groep"] = [f"csv-{i}" for i in range(len(csv))]  # elke opname-ry is 'n eie persoon
        dele.append(csv)
        print(f"Selfgerapporteerde data: {len(csv)} rye")
    if van_logs:
        from scripts.aankoms_data_uit_logs import bou_opleidingsdata
        logs = bou_opleidingsdata()
        logs["groep"] = "geb-" + logs["groep"].astype(str)
        dele.append(logs)
        print(f"Heklog-data: {len(logs)} rye van {logs['groep'].nunique()} persone")
    if not dele:
        return None, None
    df = berei_voor(pd.concat(dele, ignore_index=True))
    return df, df["groep"].to_numpy()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--van-logs", action="store_true",
                        help="Sluit onlangse kampushek-skanderings uit die databasis in.")
    args = parser.parse_args(argv)

    df, groepe = laai_data(args.van_logs)
    if df is None:
        print(f"Geen opleidingsdata nie ({DATA_PATH} ontbreek en --van-logs is nie gestel nie).")
        return 1

    n_groepe = len(np.unique(groepe))
    if len(df) < MIN_RYE or n_groepe < MIN_GROEPE:
        print(f"Te min data ({len(df)} rye, {n_groepe} persone; minimum {MIN_RYE} rye en "
              f"{MIN_GROEPE} persone). Die bestaande model bly in gebruik.")
        return 0

    # Gebruik groep-bewuste voue net as iemand meer as een ry het.
    if pd.Series(groepe).value_counts().max() == 1:
        groepe = None
    final_model = kies_en_bou_model(df, groepe)
    stoor_veilig(final_model)
    print(f"Saved {final_model['type']} model to {MODEL_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
