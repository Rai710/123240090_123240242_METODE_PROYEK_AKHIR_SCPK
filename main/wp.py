# wp.py
import numpy as np
import pandas as pd

def hitung_jarak_haversine(lat1, lon1, lat2, lon2):
    """Menghitung jarak koordinat geografis (KM)"""
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return c * 6371

def core_weighted_product(df_alternatif, bobot, jenis_kriteria, sort_order='descending'):
    """Engine utama rumus WP dengan fitur shortcut Ascend/Descend"""
    if df_alternatif.empty:
        return df_alternatif
        
    df_wp = df_alternatif.copy()
    
    # 1. Normalisasi Bobot
    total_bobot = sum(bobot.values())
    bobot_normal = {k: v / total_bobot for k, v in bobot.items()}
    
    # 2. Hitung Vektor S
    S = np.ones(len(df_wp))
    for kriteria in bobot.keys():
        w = bobot_normal[kriteria]
        if jenis_kriteria[kriteria] == 'cost':
            w = -w
        
        nilai_kolom = df_wp[kriteria].replace(0, 0.01)
        S *= nilai_kolom ** w
        
    df_wp['Vector_S'] = S
    
    # 3. Hitung Vektor V & Ranking
    df_wp['Vector_V'] = df_wp['Vector_S'] / df_wp['Vector_S'].sum()
    df_wp['Ranking'] = df_wp['Vector_V'].rank(ascending=False, method='min')
    
    # Shortcut Ascending / Descending
    is_ascending = True if sort_order == 'ascending' else False
    return df_wp.sort_values(by='Vector_V', ascending=is_ascending)