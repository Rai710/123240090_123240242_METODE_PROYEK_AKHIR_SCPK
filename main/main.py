# main.py
from pathlib import Path
import pandas as pd
import numpy as np
# Mengambil rumus dari file wp.py
from wp import core_weighted_product, hitung_jarak_haversine

# Setup Path Data Sesuai Kepunyaanmu
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent

CSV_PATH_HOTEL = PROJECT_ROOT / "dataset" / "clean" / "data_hotel_clean.csv"
CSV_PATH_PARIWISATA = PROJECT_ROOT / "dataset" / "clean" / "data_pariwisata_clean.csv"
CSV_PATH_WISATA_FINAL = PROJECT_ROOT / "dataset" / "clean" / "data_wisata_clean.csv"

# Load global data
df_hotel = pd.read_csv(CSV_PATH_HOTEL)
df_pariwisata = pd.read_csv(CSV_PATH_PARIWISATA)
df_wisata_final = pd.read_csv(CSV_PATH_WISATA_FINAL)

# Merge jarak_pusat_km + jumlah_hotel_terdekat dari data_pariwisata ke data_wisata_final
df_wisata_final = df_wisata_final.merge(
    df_pariwisata[['nama', 'jarak_pusat_km', 'jumlah_hotel_terdekat']],
    on='nama', how='left'
)
df_wisata_final['jarak_pusat_km'] = df_wisata_final['jarak_pusat_km'].fillna(df_wisata_final['jarak_pusat_km'].median())
df_wisata_final['jumlah_hotel_terdekat'] = df_wisata_final['jumlah_hotel_terdekat'].fillna(0)

# FUNGSI REKOMENDASI UTAMA & REKOMENDASI DINAMIS

def rekomendasi_wisata_dari_hotel(nama_hotel, bobot_user, budget_maks=None, kategori=None, keyword=None, sort_order='descending', hari='Weekday'):
    """Mode A: Rekomendasi Wisata + Multi-filtering + Harga Dinamis"""
    hotel_terpilih = df_hotel[df_hotel['NAMA PENGINAPAN'] == nama_hotel].iloc[0]
    
    df_dinamis = df_wisata_final.copy()

    # Hitung Jarak ke Hotel secara real-time
    df_dinamis['jarak_ke_hotel'] = hitung_jarak_haversine(
        hotel_terpilih['Latitude'], hotel_terpilih['Longitude'], 
        df_dinamis['latitude'], df_dinamis['longitude']
    )

    # Kolom harga dinamis berdasarkan pilihan hari
    harga_col = 'htm_weekday' if hari == 'Weekday' else 'htm_weekend'
    df_dinamis['harga_tiket'] = df_dinamis[harga_col]

    # Filter budget menggunakan harga dinamis
    if budget_maks:
        df_dinamis = df_dinamis[df_dinamis['harga_tiket'] <= budget_maks]
    if kategori and kategori.lower() != 'semua':
        df_dinamis = df_dinamis[df_dinamis['type'].str.lower() == kategori.lower()]
    if keyword:
        df_dinamis = df_dinamis[
            df_dinamis['nama'].str.contains(keyword, case=False) |
            df_dinamis['description'].str.contains(keyword, case=False)
        ]

    # 5 Kriteria: rating, popularitas, harga (dinamis), jarak hotel, jarak pusat kota
    jenis_kri = {
        'vote_average':   'benefit',
        'vote_count':     'benefit',
        'harga_tiket':    'cost',
        'jarak_ke_hotel': 'cost',
        'jarak_pusat_km': 'cost',
    }
    return core_weighted_product(df_dinamis, bobot_user, jenis_kri, sort_order)


def rekomendasi_hotel_dari_wisata(nama_wisata, bobot_user, sort_order='descending'):
    """Mode B: Rekomendasi Hotel terbaik berdasarkan objek wisata terpilih (4 Kriteria)"""
    wisata_terpilih = df_wisata_final[df_wisata_final['nama'] == nama_wisata].iloc[0]

    df_dinamis = df_hotel.copy()

    # Konversi teks kelas hotel menjadi angka (1-5)
    kelas_rank = {
        'Bintang Lima': 5, 'Bintang Empat': 4, 'Bintang Tiga': 3,
        'Bintang Dua': 2, 'Bintang Satu': 1, 'Melati': 1,
        'Vila': 1, 'Pondok Wisata': 1, 'Akomodasi Lain': 1
    }
    df_dinamis['GOLONGAN_SCORE'] = df_dinamis['GOLONGAN'].map(kelas_rank).fillna(1)
    df_dinamis['JUMLAH KAMAR']   = df_dinamis['JUMLAH KAMAR'].fillna(df_dinamis['JUMLAH KAMAR'].median())

    df_dinamis['jarak_ke_wisata'] = hitung_jarak_haversine(
        wisata_terpilih['latitude'], wisata_terpilih['longitude'],
        df_dinamis['Latitude'], df_dinamis['Longitude']
    )
    df_dinamis['estimasi_waktu_menit'] = (df_dinamis['jarak_ke_wisata'] / 40) * 60

    # Menggunakan 4 kriteria hotel yang efisien
    jenis_kri = {
        'JUMLAH KAMAR':         'benefit',
        'GOLONGAN_SCORE':       'benefit',
        'jarak_ke_wisata':      'cost',
        'estimasi_waktu_menit': 'cost',
    }
    
    # Mencegah error jika UI mengirimkan bobot berlebih
    bobot_aktif = {k: v for k, v in bobot_user.items() if k in jenis_kri}
    
    return core_weighted_product(df_dinamis, bobot_aktif, jenis_kri, sort_order)


def rekomendasi_wisata_global(bobot_user, kategori=None, keyword=None, budget_min=0, budget_maks=None, sort_order='descending'):
    """Mode C: Rekomendasi Wisata dengan rentang harga batas bawah dan atas"""
    df_dinamis = df_wisata_final.copy()
    
    # Pakai harga standar weekday
    df_dinamis['harga_tiket'] = df_dinamis['htm_weekday'] 
    
    # UPDATE LOGIC: Filter Rentang Budget (Min & Max)
    if budget_maks is not None:
        df_dinamis = df_dinamis[
            (df_dinamis['harga_tiket'] > budget_min) & 
            (df_dinamis['harga_tiket'] <= budget_maks)
        ]
        
    if kategori and kategori.lower() != 'semua':
        df_dinamis = df_dinamis[df_dinamis['type'].str.lower() == kategori.lower()]
    if keyword:
        df_dinamis = df_dinamis[
            df_dinamis['nama'].str.contains(keyword, case=False) |
            df_dinamis['description'].str.contains(keyword, case=False)
        ]

    jenis_kri = {
        'harga_tiket':           'cost',
        'jarak_pusat_km':        'cost',
        'jumlah_hotel_terdekat': 'benefit',
        'vote_average':          'benefit',
        'vote_count':            'benefit',
    }
    
    bobot_aktif = {k: v for k, v in bobot_user.items() if k in jenis_kri}
    
    return core_weighted_product(df_dinamis, bobot_aktif, jenis_kri, sort_order)

def buat_paket_itinerary(nama_hotel, bobot_user, radius_km=15):
    """Membuat paket rute 3 wisata terdekat dari hotel"""
    hotel_terpilih = df_hotel[df_hotel['NAMA PENGINAPAN'] == nama_hotel].iloc[0]
    df_dinamis = df_pariwisata.copy()
    df_dinamis['jarak_ke_hotel'] = hitung_jarak_haversine(
        hotel_terpilih['Latitude'], hotel_terpilih['Longitude'], df_dinamis['latitude'], df_dinamis['longitude']
    )
    
    df_radius = df_dinamis[df_dinamis['jarak_ke_hotel'] <= radius_km]
    jenis_kri = {
        'vote_average': 'benefit', 'vote_count': 'benefit',
        'htm_weekday': 'cost', 'htm_weekend': 'cost', 'jarak_ke_hotel': 'cost'
    }
    hasil = core_weighted_product(df_radius, bobot_user, jenis_kri, sort_order='descending')
    return hasil.head(3)

def hitung_analisis_sensitivitas(nama_hotel, bobot_base, kriteria_diubah, delta=1, hari='Weekday'):
    """Melihat efek pergeseran ranking jika bobot kriteria diubah"""
    df_awal = rekomendasi_wisata_dari_hotel(nama_hotel, bobot_base, hari=hari)
    df_awal_sub = df_awal[['nama', 'Ranking']].rename(columns={'Ranking': 'Rank_Awal'})
    
    bobot_baru = bobot_base.copy()
    bobot_baru[kriteria_diubah] += delta
    
    df_baru = rekomendasi_wisata_dari_hotel(nama_hotel, bobot_baru, hari=hari)
    df_baru_sub = df_baru[['nama', 'Ranking']].rename(columns={'Ranking': 'Rank_Baru'})
    
    merge_df = pd.merge(df_awal_sub, df_baru_sub, on='nama')
    merge_df['Perubahan_Posisi'] = merge_df['Rank_Awal'] - merge_df['Rank_Baru']
    return merge_df.sort_values(by='Rank_Baru').head(10)