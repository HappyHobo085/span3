import sys
import os
import json
import numpy as np
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

# Maak seker ons kan Backend modules invoer (nie streng nodig vir hierdie data as ons net CSV lees nie)
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(backend_dir, ".env"))
sys.path.append(backend_dir)

from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error

def oefen_en_voorspel():
    csv_pad = Path(__file__).parent.parent / "ml_data" / "sintetiese_lokaalgebruik.csv"
    uitset_pad = Path(__file__).parent.parent / "ml_data" / "huidige_voorspelling.json"
    
    if not csv_pad.exists():
        print(f"Fout: Kan nie {csv_pad.name} vind nie. Hardloop eers genereer_sintetiese_data.py")
        return

    print("Lees data in...")
    df = pd.read_csv(csv_pad)
    
    # Hou slegs rye waar daar wel inskrywings is
    df = df[df['Inskrywing'] > 0].copy()
    
    # Teikenveranderlike
    df['Koers'] = (df['Skanderings'] / df['Inskrywing']).clip(upper=1.0).fillna(0)

    # Omskakelings vir ML Model
    # Maak seker die datatipes is korrek vir categorical features
    df['Vak'] = df['Vak'].astype('category')
    df['Lokaal'] = df['Lokaal'].astype('category')
    df['Dag'] = df['Dag'].astype('category')
    
    # Skep 'n numeriese uur (as mens regtig wil, of net category)
    df['Begin_Uur'] = df['Begin'].str.split(':').str[0].astype(int)

    voorspellings_per_week = {}

    weke = sorted(df['Week'].unique())
    print(f"Beskikbare weke: {weke}")

    for toets_week in weke:
        toets_mask = df['Week'] == toets_week
        train_mask = df['Week'] < toets_week
        
        df_toets = df[toets_mask].copy()
        
        if toets_week == 1:
            # Week 1: Geen data in die verlede. Slegs rooster
            df_toets['Finale_Koers'] = 1.0
            df_toets['Bron'] = 'ROOSTER'
            
        elif toets_week <= 3:
            # Weke 2 en 3: 3-weke gemiddeld as basislyn, maar model kan dit nie regverdig klop weens te min data
            df_train = df[train_mask]
            
            hist_gem = df_train.groupby(['Vak', 'Lokaal'])['Koers'].mean().reset_index(name='P_3Week')
            df_toets = df_toets.merge(hist_gem, on=['Vak', 'Lokaal'], how='left')
            globale_gem = df_train['Koers'].mean()
            df_toets['P_3Week'] = df_toets['P_3Week'].fillna(globale_gem)
            
            df_toets['Finale_Koers'] = df_toets['P_3Week']
            df_toets['Bron'] = 'BASISLYN (3-Week Gemiddeld)'
            
        else:
            # Vanaf week 4
            df_train = df[train_mask].copy()
            
            # Basislyn 1: Gemiddeld van laaste 3 weke
            laaste_3 = df_train[df_train['Week'] >= toets_week - 3]
            hist_gem = laaste_3.groupby(['Vak', 'Lokaal'])['Koers'].mean().reset_index(name='P_3Week')
            df_toets = df_toets.merge(hist_gem, on=['Vak', 'Lokaal'], how='left')
            globale_gem = laaste_3['Koers'].mean()
            df_toets['P_3Week'] = df_toets['P_3Week'].fillna(globale_gem)
            
            # Basislyn 2: Dag/Uur gemiddeld
            dag_uur_gem = df_train.groupby(['Dag', 'Begin_Uur'])['Koers'].mean().reset_index(name='P_DagUur')
            df_toets = df_toets.merge(dag_uur_gem, on=['Dag', 'Begin_Uur'], how='left')
            df_toets['P_DagUur'] = df_toets['P_DagUur'].fillna(df_train['Koers'].mean())
            
            # ML Model opleiding
            features = ['Vak', 'Lokaal', 'Dag', 'Begin_Uur', 'Inskrywing']
            
            X_train = df_train[features]
            y_train = df_train['Koers']
            X_toets = df_toets[features]
            
            model = HistGradientBoostingRegressor(categorical_features=[0, 1, 2], random_state=42)
            model.fit(X_train, y_train)
            
            df_toets['P_ML'] = model.predict(X_toets).clip(0, 1)
            
            # --- EVALUASIE (Die Bootstrap Reël) ---
            # Ons simuleer asof ons model kies o.g.v validasie teen die vorige week
            df_val = df_train[df_train['Week'] == toets_week - 1].copy()
            
            if len(df_val) > 0:
                val_hist_gem = df_train[df_train['Week'] >= toets_week - 4]
                val_hist_gem = val_hist_gem[val_hist_gem['Week'] < toets_week - 1]
                
                vgem = val_hist_gem.groupby(['Vak', 'Lokaal'])['Koers'].mean().reset_index(name='P_3Week')
                df_val = df_val.merge(vgem, on=['Vak', 'Lokaal'], how='left')
                df_val['P_3Week'] = df_val['P_3Week'].fillna(val_hist_gem['Koers'].mean() if not val_hist_gem.empty else globale_gem)
                
                df_val['P_ML'] = model.predict(df_val[features]).clip(0, 1)
                
                y_val = df_val['Koers']
                
                # Paired Bootstrap
                n_boot = 1000
                verskille = []
                idx_array = np.arange(len(y_val))
                
                y_val_np = y_val.values
                p_3week_np = df_val['P_3Week'].values
                p_ml_np = df_val['P_ML'].values
                
                for _ in range(n_boot):
                    idx = np.random.choice(idx_array, size=len(idx_array), replace=True)
                    mae_base = np.mean(np.abs(y_val_np[idx] - p_3week_np[idx]))
                    mae_ml = np.mean(np.abs(y_val_np[idx] - p_ml_np[idx]))
                    verskille.append(mae_base - mae_ml) # > 0 means ML error is lower
                    
                mean_diff = np.mean(verskille)
                se_diff = np.std(verskille)
                
                if mean_diff > 0 and mean_diff >= 1.0 * se_diff:
                    # Model wen regverdig (minstens 1 SE beter as basislyn)
                    df_toets['Finale_Koers'] = df_toets['P_ML']
                    df_toets['Bron'] = 'ML MODEL'
                else:
                    df_toets['Finale_Koers'] = df_toets['P_3Week']
                    df_toets['Bron'] = 'BASISLYN (3-Week Gemiddeld)'
            else:
                df_toets['Finale_Koers'] = df_toets['P_3Week']
                df_toets['Bron'] = 'BASISLYN (3-Week Gemiddeld)'
        
        # Stoor in die dictionary
        voorspellings_per_week[int(toets_week)] = {}
        for _, row in df_toets.iterrows():
            # Die sleutel is uniek per sessie in die rooster
            key = f"{row['Vak']}_{row['Lokaal']}_{row['Dag']}_{row['Begin']}"
            voorspellings_per_week[int(toets_week)][key] = {
                "koers": float(row['Finale_Koers']),
                "bron": str(row['Bron'])
            }

    # Skryf finaal weg
    with open(out_pad, "w", encoding="utf-8") as f:
        json.dump(voorspellings_per_week, f, indent=2)
        
    print(f"Voorspellings suksesvol gegenereer vir {len(voorspellings_per_week)} weke by {out_pad.name}")

if __name__ == "__main__":
    oefen_en_voorspel()
