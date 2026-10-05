import sys
import os
import numpy as np
import pandas as pd
import joblib
import sklearn
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import KFold
from sklearn.metrics import mean_absolute_error
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OrdinalEncoder
from sklearn.pipeline import Pipeline

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from services.compatibiliteit_service import VOORSTAD_NA_KLUSTER, norm_voorstad

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "ml_data", "werklik_selfgerapporteer.csv")
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "ml_models", "aankoms_model.joblib")

def main():
    if not os.path.exists(DATA_PATH):
        print(f"File not found: {DATA_PATH}")
        sys.exit(1)

    df = pd.read_csv(DATA_PATH)
    
    # Preprocess role
    df["rol"] = df["rol"].astype(str).str.upper().replace("ALBEI", "BEIDE")
    
    # Preprocess kluster
    df["kluster"] = df["voorstad"].apply(lambda x: VOORSTAD_NA_KLUSTER.get(norm_voorstad(x), "onbekend"))
    
    # Ensure is_koshuis is numeric
    if "is_koshuis" in df.columns:
        df["is_koshuis"] = df["is_koshuis"].astype(int)
    else:
        df["is_koshuis"] = 0
        
    df["klas_begin_minuut"] = df["klas_begin_minuut"].astype(int)
    df["vroeg"] = (df["klas_begin_minuut"] <= 480).astype(int)
    
    target = "offset_tipies"
    y = df[target].values
    
    features = ["klas_begin_minuut", "kluster", "rol", "is_koshuis"]
    X = df[features].copy()

    # Define baselines
    N = len(df)
    
    # 1. Konstante 15
    pred_15 = np.full(N, 15.0)
    
    # 2. Globale Mediaan
    global_median = np.median(y)
    pred_global = np.full(N, global_median)
    
    # 3. Kluster-Mediaan (with CV-like behavior, but since it's a simple lookup, we compute out-of-fold predictions)
    # We will do a 5x10 K-Fold CV to compute OOF predictions for all models
    
    oof_15 = np.zeros((5, N))
    oof_global = np.zeros((5, N))
    oof_cluster = np.zeros((5, N))
    oof_ml_50 = np.zeros((5, N))
    oof_ml_10 = np.zeros((5, N))
    oof_ml_90 = np.zeros((5, N))
    
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

    for rep in range(5):
        kf = KFold(n_splits=10, shuffle=True, random_state=rep)
        for train_idx, test_idx in kf.split(X):
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
    best_model = "MEDIAAN" # default
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
            "rule": model_type, # "GLOBAL" or "CLUSTER"
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
    
    joblib.dump(final_model, MODEL_PATH)
    print(f"Saved {model_type} model to {MODEL_PATH}")

if __name__ == "__main__":
    main()
