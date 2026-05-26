# app.py — SPK Wisata DIY · Native Streamlit
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import matplotlib.pyplot as plt
import seaborn as sns

try:
    from main import (
        df_hotel, df_wisata_final, df_pariwisata,
        rekomendasi_wisata_dari_hotel,
        rekomendasi_hotel_dari_wisata,
        rekomendasi_wisata_global,
        hitung_analisis_sensitivitas,
    )
    from ui_components import draw_radar_chart
except ImportError as e:
    st.error(f"Gagal memuat modul: {e}")
    st.stop()

st.set_page_config(
    page_title="Jogja Tourism Recommender",
    page_icon="🏯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# SESSION STATE
if "active_mode"    not in st.session_state: st.session_state.active_mode    = "Cari Pariwisata"
if "target_wisata"  not in st.session_state: st.session_state.target_wisata  = None
if "hasil_paket"    not in st.session_state: st.session_state.hasil_paket    = pd.DataFrame()


# HELPER: SEARCH SELECTBOX
def search_selectbox(label, options, default_value=None, key_prefix=""):
    """Text input + filtered selectbox — meniru perilaku autocomplete."""
    query = st.text_input(label, placeholder="Ketik nama untuk mencari…", key=f"{key_prefix}_query")
    filtered = [o for o in options if query.lower() in o.lower()] if query else options

    if not filtered:
        st.caption("Tidak ada hasil yang cocok.")
        return default_value

    # Tentukan index default
    def_idx = 0
    if default_value and default_value in filtered:
        def_idx = filtered.index(default_value)

    return st.selectbox(
        f"Hasil pencarian ({len(filtered)} ditemukan)" if query else "Pilih dari daftar",
        filtered,
        index=def_idx,
        key=f"{key_prefix}_select",
        label_visibility="collapsed",
    )


# POPUP DIALOG
@st.dialog("Detail Destinasi")
def popup_detail_wisata(w_row):
    st.subheader(w_row["nama"])
    a, b = st.columns(2)
    a.metric("Kategori",         w_row.get("type", "—"))
    b.metric("Rating",           f"{w_row['vote_average']:.1f} / 5")
    a.metric("Harga Tiket",      f"Rp {int(w_row['harga_tiket']):,}")
    b.metric("Jarak Pusat Kota", f"{w_row['jarak_pusat_km']:.1f} km")
    a.metric("Ulasan",           f"{int(w_row['vote_count']):,} orang")
    b.metric("Hotel Terdekat",   f"{int(w_row.get('jumlah_hotel_terdekat', 0))} hotel")
    st.divider()
    st.info("Ingin melihat rekomendasi hotel khusus untuk destinasi ini?")
    if st.button("Cari Hotel untuk Destinasi Ini", type="primary", use_container_width=True):
        st.session_state.active_mode   = "Cari Hotel"  
        st.session_state.target_wisata = w_row["nama"]
        st.rerun()


#SIDEBAR
with st.sidebar:
    st.header("Panel Kendali")
    
    mode_pilih = st.radio(
        "mode",
        ["Cari Pariwisata", "Cari Hotel", "Belum Ada Tujuan", "Data & Analitik"], # <-- UBAH DI SINI
        key="active_mode",
        label_visibility="collapsed",
    )
    
    MODE_A = mode_pilih == "Cari Pariwisata"
    MODE_B = mode_pilih == "Cari Hotel"
    MODE_C = mode_pilih == "Belum Ada Tujuan"
    MODE_D = mode_pilih == "Data & Analitik"
    st.divider()

    # Default semua variabel
    hotel_pilih = wisata_pilih = None
    hari_pilih = "Weekday"
    radius_input = 15.0
    budget_min, budget_maks = 0, 100000
    kat_pilih = "Semua"
    keyword_pilih = ""
    bobot_user = bobot_hotel = bobot_wisata_global = {}
    bobot_hotel_global = {"JUMLAH KAMAR": 3, "GOLONGAN_SCORE": 3, "jarak_ke_wisata": 5, "estimasi_waktu_menit": 4}
    filter_bintang_b = filter_bintang_c = [1, 2, 3, 4, 5]

    #MODE A 
    if MODE_A:
        st.caption("HOTEL MENGINAP")
        hotel_list = sorted(df_hotel["NAMA PENGINAPAN"].dropna().unique().tolist())
        hotel_pilih = search_selectbox("Cari hotel", hotel_list, key_prefix="hotel_a")

        st.divider()
        radius_input = st.slider("Radius maksimal (km)", 1.0, 50.0, 15.0, 0.5)
        hari_pilih   = st.radio("Hari kunjungan", ["Weekday", "Weekend"], horizontal=True)

        st.divider()
        st.caption("FILTER WISATA")
        kat_pilih    = st.selectbox("Kategori", ["Semua"] + df_wisata_final["type"].dropna().unique().tolist())
        budget_maks  = st.number_input("Budget tiket maks (Rp)", min_value=0, value=100000, step=5000)
        keyword_pilih= st.text_input("Kata kunci", placeholder="Contoh: Candi, Pantai")

        st.divider()
        with st.expander("Bobot Kriteria (1–5)"):
            st.caption("Geser untuk menyesuaikan prioritas.")
            bobot_user = {
                "vote_average":   st.slider("Rating",            1, 5, 4),
                "vote_count":     st.slider("Popularitas",       1, 5, 3),
                "harga_tiket":    st.slider("Harga Tiket",       1, 5, 4),
                "jarak_ke_hotel": st.slider("Jarak dari Hotel",  1, 5, 5),
                "jarak_pusat_km": st.slider("Jarak Pusat Kota",  1, 5, 2),
            }

    # MODE B
    elif MODE_B:
        st.caption("TUJUAN WISATA")
        wisata_list = sorted(df_wisata_final["nama"].dropna().unique().tolist())
        wisata_pilih = search_selectbox(
            "Cari wisata", wisata_list,
            default_value=st.session_state.target_wisata,
            key_prefix="wisata_b",
        )

        st.divider()
        st.caption("FILTER KELAS HOTEL")
        filter_bintang_b = st.multiselect(
            "Kelas hotel",
            options=[1, 2, 3, 4, 5],
            default=[1, 2, 3, 4, 5],
            format_func=lambda x: f"Kelas {x}",
        )

        st.divider()
        with st.expander("Bobot Kriteria Hotel (1–5)"):
            bobot_hotel = {
                "JUMLAH KAMAR":         st.slider("Kapasitas Kamar",  1, 5, 3),
                "GOLONGAN_SCORE":       st.slider("Kelas Hotel",       1, 5, 4),
                "jarak_ke_wisata":      st.slider("Jarak ke Wisata",   1, 5, 5),
                "estimasi_waktu_menit": st.slider("Estimasi Waktu",    1, 5, 4),
            }

    #bODE C 
    elif MODE_C:
        st.caption("GAYA LIBURAN")
        gaya = st.selectbox(
            "Budget wisata",
            ["Hemat  (< Rp 10.000)", "Menengah  (Rp 10–50 ribu)", "Eksklusif  (> Rp 50.000)"],
        )
        if gaya.startswith("Hemat"):
            budget_min, budget_maks, def_w, bh_bintang = -1, 10000, [5,4,3,4,3], 1
        elif gaya.startswith("Menengah"):
            budget_min, budget_maks, def_w, bh_bintang = 10000, 50000, [3,3,4,4,4], 3
        else:
            budget_min, budget_maks, def_w, bh_bintang = 50000, 1_000_000, [1,2,5,5,5], 5

        st.divider()
        st.caption("FILTER DESTINASI")
        kat_pilih     = st.selectbox("Kategori", ["Semua"] + df_wisata_final["type"].dropna().unique().tolist())
        keyword_pilih = st.text_input("Kata kunci", placeholder="Contoh: Candi, Pantai")
        filter_bintang_c = st.multiselect(
            "Kelas hotel",
            options=[1, 2, 3, 4, 5],
            default=[1, 2] if gaya.startswith("Hemat") else ([3] if gaya.startswith("Menengah") else [4, 5]),
            format_func=lambda x: f"Kelas {x}",
        )

        st.divider()
        with st.expander("Bobot Kriteria Wisata (1–5)"):
            bobot_wisata_global = {
                "harga_tiket":           st.slider("Harga Tiket",        1, 5, def_w[0]),
                "jarak_pusat_km":        st.slider("Jarak Pusat Kota",   1, 5, def_w[1]),
                "jumlah_hotel_terdekat": st.slider("Hotel Terdekat",     1, 5, def_w[2]),
                "vote_average":          st.slider("Rating",              1, 5, def_w[3]),
                "vote_count":            st.slider("Popularitas",         1, 5, def_w[4]),
            }
        bobot_hotel_global = {
            "JUMLAH KAMAR": 3, "GOLONGAN_SCORE": bh_bintang,
            "jarak_ke_wisata": 5, "estimasi_waktu_menit": 4,
        }
    elif MODE_D:
        st.info("👉 Silakan lihat halaman utama (sebelah kanan) untuk melihat data dan analitik.")


# HEADER
col_ttl, col_stat = st.columns([3, 1])
with col_ttl:
    st.title("Jogja Tourism — Recommender")
    st.caption("Sistem Pendukung Keputusan · Metode Weighted Product · Reinnent Rasika Z & Tim")
with col_stat:
    with st.container(border=True):
        a, b = st.columns(2)
        a.metric("Hotel",  f"{len(df_hotel):,}")
        b.metric("Wisata", f"{len(df_wisata_final):,}")

st.divider()


# ── TABS

if MODE_A:
    tab1, tab2, tab3 = st.tabs(["Rekomendasi Wisata", "Peta Lokasi", "Sensitivitas Bobot"])
elif MODE_B:
    tab1, tab2 = st.tabs(["Rekomendasi Hotel", "Peta Lokasi"])
elif MODE_C:
    tab1, tab2 = st.tabs(["Paket Liburan", "Peta Lokasi"])
elif MODE_D:
    tab_profil, tab_data, tab_grafik = st.tabs(["👥 Profil Kelompok", "📂 Dataset Mentah", "📈 Visualisasi Analitik"])



# MODE A

if MODE_A:
    with tab1:
        st.subheader("Rekomendasi Wisata Terbaik")
        if hotel_pilih:
            st.caption(f"Hotel: **{hotel_pilih}** · Radius: **{radius_input} km** · Hari: **{hari_pilih}**")
        else:
            st.warning("Pilih hotel terlebih dahulu di panel kiri.")

        if hotel_pilih and st.button("Hitung Rekomendasi", type="primary", use_container_width=True):
            with st.spinner("Memproses algoritma Weighted Product…"):
                hasil_mentah = rekomendasi_wisata_dari_hotel(
                    hotel_pilih, bobot_user, budget_maks, kat_pilih, keyword_pilih, "descending", hari_pilih
                )
                hasil = hasil_mentah[hasil_mentah["jarak_ke_hotel"] <= radius_input]

            if hasil.empty:
                st.warning(f"Tidak ada destinasi dalam radius {radius_input} km dengan budget yang dipilih.")
            else:
                juara = hasil.iloc[0]
                with st.container(border=True):
                    kol_badge, _ = st.columns([1, 4])
                    kol_badge.success("Peringkat #1")
                    st.subheader(juara["nama"])
                    st.caption(f"{juara.get('type','—')}  ·  Skor WP: {juara['Vector_V']:.6f}")
                    m1, m2, m3, m4, m5 = st.columns(5)
                    m1.metric("Rating",       f"{juara['vote_average']:.1f} / 5")
                    m2.metric("Ulasan",        f"{int(juara['vote_count']):,}")
                    m3.metric("Harga",         f"Rp {int(juara['harga_tiket']):,}")
                    m4.metric("Jarak Hotel",   f"{juara['jarak_ke_hotel']:.1f} km")
                    m5.metric("Jarak Pusat",   f"{juara['jarak_pusat_km']:.1f} km")

                st.divider()
                col_c, col_t = st.columns([1, 1], gap="large")
                with col_c:
                    st.subheader("Profil Atribut")
                    st.caption("Perbandingan top-2 rekomendasi (skala 0–100)")
                    draw_radar_chart(
                        hasil.head(2),
                        labels=["Rating", "Popularitas", "Harga", "Jarak Hotel", "Jarak Pusat"],
                        keys=["vote_average","vote_count","harga_tiket","jarak_ke_hotel","jarak_pusat_km"],
                        costs=[False, False, True, True, True],
                    )
                with col_t:
                    st.subheader("Peringkat Lengkap")
                    st.caption(f"Top 10 dari {len(hasil)} destinasi yang memenuhi filter")
                    df_show = hasil[["Ranking","nama","type","vote_average","harga_tiket",
                                     "jarak_ke_hotel","jarak_pusat_km","Vector_V"]].head(10).copy()
                    st.dataframe(
                        df_show, use_container_width=True, hide_index=True,
                        column_config={
                            "Ranking":       st.column_config.NumberColumn("#",           width="small"),
                            "nama":          st.column_config.TextColumn("Destinasi",     width="medium"),
                            "type":          st.column_config.TextColumn("Kategori",      width="small"),
                            "vote_average":  st.column_config.NumberColumn("Rating",      format="%.1f", width="small"),
                            "harga_tiket":   st.column_config.NumberColumn("Harga (Rp)",  format="Rp %d", width="small"),
                            "jarak_ke_hotel":st.column_config.NumberColumn("Jarak Hotel", format="%.1f km", width="small"),
                            "jarak_pusat_km":st.column_config.NumberColumn("Jarak Pusat", format="%.1f km", width="small"),
                            "Vector_V":      st.column_config.NumberColumn("Skor WP",     format="%.5f", width="small"),
                        },
                    )

    with tab2:
        st.subheader("Peta Persebaran Wisata")
        st.caption("Merah = hotel Anda · Biru = rekomendasi destinasi terdekat")
        if hotel_pilih and st.button("Tampilkan Peta", type="primary"):
            with st.spinner("Memuat peta…"):
                h_data = df_hotel[df_hotel["NAMA PENGINAPAN"] == hotel_pilih].iloc[0]
                m = folium.Map(location=[h_data["Latitude"], h_data["Longitude"]], zoom_start=13)
                folium.Marker(
                    [h_data["Latitude"], h_data["Longitude"]],
                    popup=hotel_pilih, tooltip="Hotel Anda",
                    icon=folium.Icon(color="red", icon="home", prefix="fa"),
                ).add_to(m)
                peta_data = rekomendasi_wisata_dari_hotel(
                    hotel_pilih, bobot_user, budget_maks, kat_pilih, keyword_pilih, "descending", hari_pilih
                )
                for _, row in peta_data[peta_data["jarak_ke_hotel"] <= radius_input].head(10).iterrows():
                    folium.Marker(
                        [row["latitude"], row["longitude"]],
                        popup=f"#{int(row['Ranking'])}: {row['nama']}",
                        tooltip=row["nama"],
                        icon=folium.Icon(color="blue", icon="star", prefix="fa"),
                    ).add_to(m)
                st_folium(m, width=None, height=500, returned_objects=[])
        elif not hotel_pilih:
            st.info("Pilih hotel di panel kiri terlebih dahulu.")
        else:
            st.info("Tekan tombol di atas untuk memuat peta interaktif.")

    with tab3:
        st.subheader("Analisis Sensitivitas Bobot")
        st.caption("Lihat pergeseran ranking jika bobot satu kriteria dinaikkan +2.")
        if hotel_pilih:
            label_kri = {
                "vote_average":   "Rating",
                "vote_count":     "Popularitas",
                "harga_tiket":    "Harga Tiket",
                "jarak_ke_hotel": "Jarak dari Hotel",
                "jarak_pusat_km": "Jarak Pusat Kota",
            }
            kri_tes = st.selectbox(
                "Kriteria yang diuji",
                options=list(label_kri.keys()),
                format_func=lambda k: label_kri[k],
            )
            if st.button("Jalankan Analisis", type="primary"):
                with st.spinner("Menganalisis…"):
                    tabel_sens = hitung_analisis_sensitivitas(hotel_pilih, bobot_user, kri_tes, delta=2, hari=hari_pilih)
                st.info(f"Bobot **{label_kri[kri_tes]}** dinaikkan +2. Positif = ranking naik, negatif = turun.")
                st.dataframe(
                    tabel_sens, use_container_width=True, hide_index=True,
                    column_config={
                        "nama":             st.column_config.TextColumn("Destinasi"),
                        "Rank_Awal":        st.column_config.NumberColumn("Rank Sebelum", width="small"),
                        "Rank_Baru":        st.column_config.NumberColumn("Rank Sesudah", width="small"),
                        "Perubahan_Posisi": st.column_config.NumberColumn("Perubahan",    width="small"),
                    },
                )
        else:
            st.info("Pilih hotel di panel kiri terlebih dahulu.")



# MODE B
elif MODE_B:
    with tab1:
        if not wisata_pilih:
            st.info("Pilih destinasi tujuan di panel kiri.")
        else:
            info_w = df_wisata_final[df_wisata_final["nama"] == wisata_pilih].iloc[0]
            with st.container(border=True):
                st.caption("DESTINASI TUJUAN")
                st.subheader(info_w["nama"])
                ia, ib, ic, id_ = st.columns(4)
                ia.metric("Kategori",       info_w.get("type", "—"))
                ib.metric("Rating",         f"{info_w['vote_average']:.1f} / 5")
                ic.metric("Hotel Terdekat", f"{int(info_w.get('jumlah_hotel_terdekat', 0))}")
                id_.metric("Jarak Pusat",   f"{info_w['jarak_pusat_km']:.1f} km")

            st.subheader("Rekomendasi Hotel Terdekat")
            st.caption("Weighted Product · 4 kriteria: kelas, kapasitas, jarak, estimasi waktu tempuh")

            if st.button("Cari Hotel Terbaik", type="primary", use_container_width=True):
                with st.spinner("Menghitung rekomendasi hotel…"):
                    hasil_hotel = rekomendasi_hotel_dari_wisata(wisata_pilih, bobot_hotel, "descending")
                    if filter_bintang_b:
                        hasil_hotel = hasil_hotel[hasil_hotel["GOLONGAN_SCORE"].isin(filter_bintang_b)]

                if hasil_hotel.empty:
                    st.warning("Tidak ada hotel yang sesuai filter kelas yang dipilih.")
                else:
                    juara_h = hasil_hotel.iloc[0]
                    with st.container(border=True):
                        kol_badge, _ = st.columns([1, 4])
                        kol_badge.success("Hotel #1")
                        st.subheader(juara_h["NAMA PENGINAPAN"])
                        st.caption(f"{juara_h['GOLONGAN']}  ·  Skor WP: {juara_h['Vector_V']:.6f}")
                        h1, h2, h3, h4 = st.columns(4)
                        h1.metric("Golongan",       juara_h["GOLONGAN"])
                        h2.metric("Jumlah Kamar",   f"{int(juara_h['JUMLAH KAMAR'])}")
                        h3.metric("Jarak ke Wisata", f"{juara_h['jarak_ke_wisata']:.1f} km")
                        h4.metric("Estimasi Waktu", f"{int(juara_h['estimasi_waktu_menit'])} menit")

                    st.divider()
                    col_c, col_t = st.columns([1, 1], gap="large")
                    with col_c:
                        st.subheader("Profil Hotel")
                        st.caption("Perbandingan top-2 (skala 0–100)")
                        draw_radar_chart(
                            hasil_hotel.head(2),
                            labels=["Kapasitas", "Kelas", "Jarak", "Waktu Tempuh"],
                            keys=["JUMLAH KAMAR","GOLONGAN_SCORE","jarak_ke_wisata","estimasi_waktu_menit"],
                            costs=[False, False, True, True],
                        )
                    with col_t:
                        st.subheader("Peringkat Hotel")
                        st.caption(f"Top 10 dari {len(hasil_hotel)} hotel")
                        df_h = hasil_hotel[[
                            "Ranking","NAMA PENGINAPAN","GOLONGAN","JUMLAH KAMAR",
                            "jarak_ke_wisata","estimasi_waktu_menit","Vector_V"
                        ]].head(10).copy()
                        st.dataframe(
                            df_h, use_container_width=True, hide_index=True,
                            column_config={
                                "Ranking":              st.column_config.NumberColumn("#",          width="small"),
                                "NAMA PENGINAPAN":      st.column_config.TextColumn("Nama Hotel",   width="medium"),
                                "GOLONGAN":             st.column_config.TextColumn("Golongan",     width="small"),
                                "JUMLAH KAMAR":         st.column_config.NumberColumn("Kamar",      format="%d", width="small"),
                                "jarak_ke_wisata":      st.column_config.NumberColumn("Jarak",      format="%.1f km", width="small"),
                                "estimasi_waktu_menit": st.column_config.NumberColumn("Estimasi",   format="%d mnt", width="small"),
                                "Vector_V":             st.column_config.NumberColumn("Skor WP",    format="%.5f", width="small"),
                            },
                        )

    with tab2:
        st.subheader("Peta Hotel Sekitar Wisata")
        st.caption("Merah = destinasi tujuan · Biru = hotel rekomendasi")
        if wisata_pilih and st.button("Tampilkan Peta", type="primary"):
            with st.spinner("Memuat peta…"):
                w_data = df_wisata_final[df_wisata_final["nama"] == wisata_pilih].iloc[0]
                m = folium.Map(location=[w_data["latitude"], w_data["longitude"]], zoom_start=13)
                folium.Marker(
                    [w_data["latitude"], w_data["longitude"]],
                    popup=wisata_pilih, tooltip="Destinasi Tujuan",
                    icon=folium.Icon(color="red", icon="flag", prefix="fa"),
                ).add_to(m)
                for _, row in rekomendasi_hotel_dari_wisata(wisata_pilih, bobot_hotel).head(10).iterrows():
                    folium.Marker(
                        [row["Latitude"], row["Longitude"]],
                        popup=f"#{int(row['Ranking'])}: {row['NAMA PENGINAPAN']}",
                        tooltip=row["NAMA PENGINAPAN"],
                        icon=folium.Icon(color="blue", icon="bed", prefix="fa"),
                    ).add_to(m)
                st_folium(m, width=None, height=500, returned_objects=[])
        elif not wisata_pilih:
            st.info("Pilih destinasi di panel kiri terlebih dahulu.")
        else:
            st.info("Tekan tombol di atas untuk memuat peta interaktif.")


# MODE C
elif MODE_C:      
    with tab1:
        st.subheader("Paket Liburan Jogja")
        st.caption("Sistem memilihkan destinasi terbaik sesuai gaya liburan, lengkap dengan opsi hotel terdekat.")

        if st.button("Racik Paket Liburan", type="primary", use_container_width=True):
            with st.spinner("Menganalisis data wisata se-Jogja…"):
                st.session_state.hasil_paket = rekomendasi_wisata_global(
                    bobot_wisata_global, kat_pilih, keyword_pilih, budget_min, budget_maks
                ).head(5)

        if not st.session_state.hasil_paket.empty:
            st.divider()
            st.caption("TOP 5 PAKET REKOMENDASI")

            for i, (_, w_row) in enumerate(st.session_state.hasil_paket.iterrows()):
                with st.container(border=True):
                    rank_col, detail_col, hotel_col, aksi_col = st.columns(
                        [0.5, 2, 3, 0.8], vertical_alignment="center"
                    )
                    rank_col.subheader(f"#{i+1}")

                    with detail_col:
                        st.markdown(f"**{w_row['nama']}**")
                        st.caption(
                            f"{w_row.get('type','—')}  ·  "
                            f"Rating {w_row['vote_average']}  ·  "
                            f"Rp {int(w_row['harga_tiket']):,}  ·  "
                            f"{w_row['jarak_pusat_km']:.1f} km dari pusat kota"
                        )

                    with hotel_col:
                        hasil_h = rekomendasi_hotel_dari_wisata(w_row["nama"], bobot_hotel_global)
                        if filter_bintang_c:
                            hasil_h = hasil_h[hasil_h["GOLONGAN_SCORE"].isin(filter_bintang_c)]
                        top3 = hasil_h.head(3)
                        if top3.empty:
                            st.caption("Tidak ada hotel sesuai kelas yang dipilih.")
                        else:
                            for _, h in top3.iterrows():
                                st.caption(
                                    f"{h['NAMA PENGINAPAN']}  ·  "
                                    f"{h['jarak_ke_wisata']:.1f} km  ·  "
                                    f"Kelas {int(h['GOLONGAN_SCORE'])}"
                                )

                    if aksi_col.button("Detail", key=f"detail_{i}", use_container_width=True):
                        popup_detail_wisata(w_row)
        else:
            st.info("Tekan tombol Racik Paket Liburan untuk memulai.")

    with tab2:
        st.subheader("Peta Destinasi Paket")
        st.caption("Hijau = destinasi dari paket yang sudah dihasilkan")
        if st.button("Tampilkan Peta", type="primary"):
            with st.spinner("Memuat peta…"):
                m = folium.Map(location=[-7.7956, 110.3695], zoom_start=11)
                if not st.session_state.hasil_paket.empty:
                    for _, w in st.session_state.hasil_paket.iterrows():
                        folium.Marker(
                            [w["latitude"], w["longitude"]],
                            popup=w["nama"], tooltip=w["nama"],
                            icon=folium.Icon(color="green", icon="star", prefix="fa"),
                        ).add_to(m)
                st_folium(m, width=None, height=500, returned_objects=[])
        else:
            st.info("Hasilkan paket terlebih dahulu, lalu tekan tombol untuk melihat peta.")

elif MODE_D:
    # --- TAB 1: PROFIL KELOMPOK ---
    with tab_profil:
        with st.container(border=True):
            st.subheader("Tim Pengembang SPK")
            st.write("Aplikasi Sistem Pendukung Keputusan (Metode Weighted Product) ini dikembangkan oleh:")
            st.markdown("- **Raihan Buono Putra**")
            st.markdown("- **Reinnent Rasika Z**")
            st.caption("Praktikum Sistem Pendukung Keputusan (SCPK) - 2026")
            
    # --- TAB 2: DATASET MENTAH ---
    with tab_data:
        st.subheader("1. Dataset Wisata Gabungan (Fitur SPK)")
        st.caption("Gabungan data dasar wisata dengan ekstraksi fitur geospasial.")
        st.dataframe(df_wisata_final, use_container_width=True, height=250)
        
        st.subheader("2. Dataset Pariwisata (Fitur Ekstraksi Jarak)")
        st.caption("Hasil perhitungan Haversine dari notebook pre-processing.")
        st.dataframe(df_pariwisata, use_container_width=True, height=250)
        
        st.subheader("3. Dataset Hotel (Cleaned)")
        st.caption("Data hotel bersih yang siap digunakan untuk kalkulasi jarak.")
        st.dataframe(df_hotel, use_container_width=True, height=250)
        
    # --- TAB 3: VISUALISASI 3 GRAFIK (SYARAT WAJIB) ---
    with tab_grafik:
        st.info("Visualisasi Exploratory Data Analysis (EDA) menggunakan Seaborn dan Matplotlib.")
        c1, c2 = st.columns(2)
        
        # Grafik 1: Bar Chart (Distribusi Kategori Wisata)
        with c1:
            st.write("**1. Distribusi Kategori Wisata di Yogyakarta**")
            fig1, ax1 = plt.subplots(figsize=(6, 4))
            sns.countplot(data=df_wisata_final, y='type', order=df_wisata_final['type'].value_counts().index, palette='viridis', ax=ax1)
            ax1.set_xlabel("Jumlah Destinasi")
            ax1.set_ylabel("Kategori")
            st.pyplot(fig1)
            
        # Grafik 2: Pie Chart (Komposisi Kelas Hotel)
        with c2:
            st.write("**2. Komposisi Ketersediaan Kelas Hotel**")
            fig2, ax2 = plt.subplots(figsize=(6, 4))
            hotel_counts = df_hotel['GOLONGAN'].value_counts().head(5)
            ax2.pie(hotel_counts, labels=hotel_counts.index, autopct='%1.1f%%', colors=sns.color_palette('pastel'))
            st.pyplot(fig2)
            
        st.divider()
        
        # Grafik 3: Scatter Plot (Korelasi Harga & Rating)
        st.write("**3. Pemetaan Harga Tiket (Weekday) vs Rating Wisata**")
        fig3, ax3 = plt.subplots(figsize=(10, 4))
        sns.scatterplot(data=df_wisata_final, x='htm_weekday', y='vote_average', hue='type', palette='Set2', alpha=0.8, ax=ax3)
        ax3.set_xlabel("Harga Tiket (Rp)")
        ax3.set_ylabel("Rating (⭐)")
        ax3.legend(title='Kategori', bbox_to_anchor=(1.05, 1), loc='upper left')
        st.pyplot(fig3)