# app.py — SPK Wisata DIY (Pure Python + Tabel + Popup & Redirect)
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from streamlit_extras.metric_cards import style_metric_cards

try:
    from main import (
        df_hotel, df_wisata_final, rekomendasi_wisata_dari_hotel, 
        rekomendasi_hotel_dari_wisata, rekomendasi_wisata_global
    )
    from ui_components import (
        ui_header, ui_section, ui_card_juara, draw_radar_chart
    )
except ImportError as e:
    st.error(f"Gagal memuat modul: {e}")
    st.stop()

st.set_page_config(page_title="Jogja Tourism SPK", page_icon="🏯", layout="wide")

# ── 1. MANAJEMEN SESI (STATE) ───────────────────────────────────────────────
# Ini fungsinya agar kita bisa pindah-pindah mode lewat tombol Pop-up
if 'active_mode' not in st.session_state:
    st.session_state.active_mode = "🎒 Belum ada rencana"
if 'target_wisata' not in st.session_state:
    st.session_state.target_wisata = None
if 'hasil_paket' not in st.session_state:
    st.session_state.hasil_paket = pd.DataFrame()

# ── 2. FUNGSI POP-UP (DIALOG) ───────────────────────────────────────────────
@st.dialog("🔍 Detail Destinasi & Lanjut Cari Hotel")
def popup_detail_wisata(w_row):
    st.write(f"### {w_row['nama']}")
    st.write(f"**Kategori:** {w_row.get('type', '-')}")
    st.write(f"**Rating:** ⭐ {w_row['vote_average']} ({int(w_row['vote_count'])} ulasan)")
    st.write(f"**Harga Tiket:** Rp {int(w_row['harga_tiket']):,}")
    st.write(f"**Jarak dari Pusat Kota:** {w_row['jarak_pusat_km']:.2f} km")
    
    st.divider()
    st.info("💡 Ingin melihat rekomendasi hotel lengkap dan detail jaraknya khusus untuk destinasi ini?")
    
    if st.button("Lanjut ke Mode B (Cari Hotel Saja)", type="primary", use_container_width=True):
        st.session_state.active_mode = "🔍 Belum punya hotel"
        st.session_state.target_wisata = w_row['nama']
        st.rerun() # Refresh halaman secara otomatis!

# ── 3. SIDEBAR LOGIC ────────────────────────────────────────────────────────
with st.sidebar:
    st.title("Panel Kendali")
    
    # Radio button sekarang nyambung ke Session State
    mode_pilih = st.radio(
        "Status Akomodasi", 
        ["🏨 Sudah punya hotel", "🔍 Belum punya hotel", "🎒 Belum ada rencana"], 
        key='active_mode',
        label_visibility="collapsed"
    )
    MODE_A = mode_pilih.startswith("🏨")
    MODE_B = mode_pilih.startswith("🔍")
    MODE_C = mode_pilih.startswith("🎒")
    st.divider()

    hotel_pilih, wisata_pilih, hari_pilih = None, None, "Weekday"
    radius_input, budget_min, budget_maks = 15.0, 0, 100000
    kat_pilih, keyword_pilih = "Semua", ""
    bobot_user, bobot_hotel, bobot_wisata_global, bobot_hotel_global = {}, {}, {}, {}

    if MODE_A:
        hotel_pilih = st.selectbox("Hotel Menginap", df_hotel['NAMA PENGINAPAN'].dropna().unique().tolist())
        radius_input = st.slider("Jarak Maksimal (KM)", 1.0, 50.0, 15.0, 0.5)
        hari_pilih = st.radio("Hari Kunjungan", ["Weekday", "Weekend"], horizontal=True)
        st.divider()
        kat_pilih = st.selectbox("Kategori Wisata", ["Semua"] + df_wisata_final['type'].dropna().unique().tolist())
        budget_maks = st.number_input(f"Budget Maks (Rp)", min_value=0, value=100000, step=5000)
        keyword_pilih = st.text_input("Kata Kunci (Opsional)")
        st.divider()
        with st.expander("⚙️ Atur Bobot Kriteria", expanded=False):
            bobot_user = {
            'vote_average': st.slider("⭐ Rating", 1, 5, 4),
            'harga_tiket': st.slider("💰 Harga", 1, 5, 4), 'jarak_ke_hotel': st.slider("📍 Jarak Hotel", 1, 5, 5),
            'jarak_pusat_km': st.slider("🏙️ Jarak Pusat", 1, 5, 2)
        }

    elif MODE_B:
        # Menangkap data dari Mode C (Redirect)
        wisata_list = df_wisata_final['nama'].dropna().sort_values().tolist()
        def_idx = 0
        if st.session_state.target_wisata in wisata_list:
            def_idx = wisata_list.index(st.session_state.target_wisata)
            
        wisata_pilih = st.selectbox("Tujuan Wisata", wisata_list, index=def_idx)
        st.divider()
        
        filter_bintang_b = st.multiselect(
            "Filter Budget / Kelas Hotel",
            options=[1, 2, 3, 4, 5],
            default=[1, 2, 3, 4, 5],
            format_func=lambda x: f"⭐ Bintang {x}"
        )
        st.divider()
        st.write("Bobot Hotel (1-5)")
        bobot_hotel = {
            'JUMLAH KAMAR': st.slider("🛏️ Kapasitas Kamar", 1, 5, 3),
            'GOLONGAN_SCORE': st.slider("🏅 Kelas Hotel", 1, 5, 4),
            'jarak_ke_wisata': st.slider("📍 Jarak Wisata", 1, 5, 5),
            'estimasi_waktu_menit': st.slider("⏱️ Waktu Tempuh", 1, 5, 4)
        }

    elif MODE_C:
        gaya_liburan = st.selectbox("Kategori Budget Wisata", ["🟢 Hemat (< Rp 10rb)", "🟡 Menengah (Rp 10rb - 50rb)", "🔵 Eksklusif (> Rp 50rb)"])
        filter_bintang_c = st.multiselect(
            "Filter Budget / Kelas Hotel",
            options=[1, 2, 3, 4, 5],
            default=[1, 2] if gaya_liburan.startswith("🟢") else ([3] if gaya_liburan.startswith("🟡") else [4, 5]),
            format_func=lambda x: f"⭐ Bintang {x}"
        )
        st.divider()
        kat_pilih = st.selectbox("Kategori Wisata", ["Semua"] + df_wisata_final['type'].dropna().unique().tolist())
        keyword_pilih = st.text_input("Kata Kunci (Opsional)")
        st.divider()
        
        if gaya_liburan.startswith("🟢"): budget_min, budget_maks, bh_bintang, def_w = -1, 10000, 1, [5, 4, 3, 4, 3]
        elif gaya_liburan.startswith("🟡"): budget_min, budget_maks, bh_bintang, def_w = 10000, 50000, 3, [3, 3, 4, 4, 4]
        else: budget_min, budget_maks, bh_bintang, def_w = 50000, 1000000, 5, [1, 2, 5, 5, 5]

        with st.expander("Kustom Bobot Wisata (Edit)"):
            bobot_wisata_global = {
                'harga_tiket': st.slider("💰 Harga Tiket", 1, 5, def_w[0]), 'jarak_pusat_km': st.slider("🏙️ Jarak Pusat", 1, 5, def_w[1]),
                'jumlah_hotel_terdekat': st.slider("🏨 Jml Hotel Terdekat", 1, 5, def_w[2]), 'vote_average': st.slider("⭐ Rating", 1, 5, def_w[3]),
                'vote_count': st.slider("💬 Popularitas", 1, 5, def_w[4])
            }
        bobot_hotel_global = {'JUMLAH KAMAR': 3, 'GOLONGAN_SCORE': bh_bintang, 'jarak_ke_wisata': 5, 'estimasi_waktu_menit': 4}

# ── 4. MAIN CONTENT ─────────────────────────────────────────────────────────
ui_header()
tab1, tab2 = st.tabs(["✦ Rekomendasi", "✦ Peta Lokasi"])

with tab1:
    if MODE_A:
        ui_section("Rekomendasi Wisata Terbaik")
        if st.button("Hitung Rekomendasi", type="primary"):
            with st.spinner("Memproses..."):
                hasil_mentah = rekomendasi_wisata_dari_hotel(hotel_pilih, bobot_user, budget_maks, kat_pilih, keyword_pilih, 'descending', hari_pilih)
                hasil = hasil_mentah[hasil_mentah['jarak_ke_hotel'] <= radius_input]

            if not hasil.empty:
                juara = hasil.iloc[0]
                ui_card_juara(1, juara.get('type','—'), juara['nama'], juara['Vector_V'])

                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("⭐ Rating", f"{juara['vote_average']:.1f}/5")
                c2.metric("💬 Ulasan", f"{int(juara['vote_count']):,}")
                c3.metric("💰 Harga", f"Rp {int(juara['harga_tiket']):,}")
                c4.metric("📍 Jarak Hotel", f"{juara['jarak_ke_hotel']:.2f} km")
                c5.metric("🏙️ Jarak Pusat", f"{juara['jarak_pusat_km']:.2f} km")
                style_metric_cards(background_color="#1E1E1E", border_left_color="#6359FF", border_color="#333333", box_shadow=False)

                st.divider()
                col_radar, col_table = st.columns([1, 1], gap="large")
                with col_radar:
                    ui_section("Profil Atribut")
                    draw_radar_chart(hasil_mentah, labels=['Rating', 'Popularitas', 'Harga', 'Jarak Hotel', 'Jarak Pusat'], keys=['vote_average', 'vote_count', 'harga_tiket', 'jarak_ke_hotel', 'jarak_pusat_km'], costs=[False, False, True, True, True])
                with col_table:
                    ui_section("Peringkat Lengkap", "Top 10 destinasi sesuai filter")
                    # Pilih semua kriteria (5 kriteria + Ranking + Nama)
                    df_show = hasil[['Ranking','nama','type','vote_average','vote_count','harga_tiket','jarak_ke_hotel','jarak_pusat_km','Vector_V']].head(10).copy()
                    
                    df_show.rename(columns={
                        'Ranking':'#', 'nama':'Destinasi', 'type':'Kategori', 
                        'vote_average':'Rating', 'vote_count':'Popularitas', 
                        'harga_tiket':'Tiket', 'jarak_ke_hotel':'Jarak Hotel', 
                        'jarak_pusat_km':'Jarak Pusat', 'Vector_V':'Skor'
                    }, inplace=True)
                    
                    # Format angka biar cantik (1 angka belakang koma)
                    df_show['Jarak Hotel'] = df_show['Jarak Hotel'].apply(lambda x: f"{x:.1f} km")
                    df_show['Jarak Pusat'] = df_show['Jarak Pusat'].apply(lambda x: f"{x:.1f} km")
                    df_show['Tiket'] = df_show['Tiket'].apply(lambda x: f"Rp {int(x):,}")
                    df_show['Skor'] = df_show['Skor'].map('{:.4f}'.format)
                    
                    st.dataframe(df_show, use_container_width=True, hide_index=True)
    elif MODE_B:
        ui_section(f"Rekomendasi Hotel Sekitar: {wisata_pilih}")
        if st.button("Cari Hotel Terbaik", type="primary"):
            with st.spinner("Menghitung..."):
                hasil_hotel = rekomendasi_hotel_dari_wisata(wisata_pilih, bobot_hotel, 'descending')
                # Terapkan Filter Budget Bintang
                if filter_bintang_b:
                    hasil_hotel = hasil_hotel[hasil_hotel['GOLONGAN_SCORE'].isin(filter_bintang_b)]

            if not hasil_hotel.empty:
                juara = hasil_hotel.iloc[0]
                ui_card_juara(1, "Akomodasi", juara['NAMA PENGINAPAN'], juara['Vector_V'], is_hotel=True)

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("🏅 Kelas Hotel", "⭐" * int(juara['GOLONGAN_SCORE']))
                c2.metric("🛏️ Kamar", f"{int(juara['JUMLAH KAMAR'])}")
                c3.metric("📍 Jarak Wisata", f"{juara['jarak_ke_wisata']:.2f} km")
                c4.metric("⏱️ Waktu Tempuh", f"{int(juara['estimasi_waktu_menit'])} mnt")
                style_metric_cards(background_color="#1E1E1E", border_left_color="#FFB400", border_color="#333333", box_shadow=False)

                st.divider()
                col_radar, col_table = st.columns([1, 1], gap="large")
                with col_radar:
                    ui_section("Profil Hotel")
                    draw_radar_chart(hasil_hotel, labels=['Kapasitas Kamar', 'Kelas Hotel', 'Jarak ke Wisata', 'Estimasi Waktu'], keys=['JUMLAH KAMAR', 'GOLONGAN_SCORE', 'jarak_ke_wisata', 'estimasi_waktu_menit'], costs=[False, False, True, True])
                with col_table:
                    ui_section("Peringkat Lengkap", "Top 10 hotel terdekat")
                    # Pilih semua kriteria (4 kriteria + Ranking + Nama)
                    df_show = hasil_hotel[['Ranking','NAMA PENGINAPAN','GOLONGAN_SCORE','JUMLAH KAMAR','jarak_ke_wisata','estimasi_waktu_menit','Vector_V']].head(10).copy()
                    
                    df_show.rename(columns={
                        'Ranking':'#', 'NAMA PENGINAPAN':'Hotel', 'GOLONGAN_SCORE':'Bintang', 
                        'JUMLAH KAMAR':'Kamar', 'jarak_ke_wisata':'Jarak', 
                        'estimasi_waktu_menit':'Waktu', 'Vector_V':'Skor'
                    }, inplace=True)
                    
                    # Format angka biar cantik
                    df_show['Jarak'] = df_show['Jarak'].apply(lambda x: f"{x:.1f} km")
                    df_show['Waktu'] = df_show['Waktu'].apply(lambda x: f"{int(x)} mnt")
                    df_show['Skor'] = df_show['Skor'].map('{:.4f}'.format)
                    
                    st.dataframe(df_show, use_container_width=True, hide_index=True)
            else:
                st.warning("Tidak ada hotel yang sesuai dengan filter bintang Anda di sekitar area tersebut.")

    elif MODE_C:
        ui_section("📦 Rekomendasi Paket Liburan")
        if st.button("Racik Paket Liburan", type="primary"):
            with st.spinner("Menganalisis data se-Jogja..."):
                st.session_state.hasil_paket = rekomendasi_wisata_global(bobot_wisata_global, kat_pilih, keyword_pilih, budget_min, budget_maks).head(5)
                
        # Menampilkan Tabel Paket yang Tersimpan di Session
        if not st.session_state.hasil_paket.empty:
            st.divider()
            
            # HEADER TABEL (Desain Rapi Pakai Kolom)
            h1, h2, h3, h4 = st.columns([2.5, 1, 3.5, 1])
            h1.caption("📍 DESTINASI UTAMA")
            h2.caption("🎟️ HARGA TIKET")
            h3.caption("🏨 TOP 3 HOTEL TERDEKAT")
            h4.caption("Aksi")
            
            # ISI TABEL
            for i, (_, w_row) in enumerate(st.session_state.hasil_paket.iterrows()):
                with st.container(border=True): # Bikin Border supaya menyerupai baris tabel
                    c1, c2, c3, c4 = st.columns([2.5, 1, 3.5, 1], vertical_alignment="center")
                    
                    c1.write(f"**{w_row['nama']}**")
                    c1.caption(f"⭐ {w_row['vote_average']}")
                    
                    c2.write(f"Rp {int(w_row['harga_tiket']):,}")
                    
                    # Logika Pencarian Top 3 Hotel sesuai Filter
                    hasil_h = rekomendasi_hotel_dari_wisata(w_row['nama'], bobot_hotel_global)
                    if filter_bintang_c:
                        hasil_h = hasil_h[hasil_h['GOLONGAN_SCORE'].isin(filter_bintang_c)]
                    
                    top_3 = hasil_h.head(3)
                    if top_3.empty:
                        c3.warning("Tidak ada hotel sesuai filter.")
                    else:
                        hotels_txt = "\n".join([f"- {h['NAMA PENGINAPAN']} (⭐{int(h['GOLONGAN_SCORE'])})" for _, h in top_3.iterrows()])
                        c3.markdown(hotels_txt)
                    
                    # TOMBOL POPUP
                    if c4.button("🔍 Detail", key=f"btn_{i}", use_container_width=True):
                        popup_detail_wisata(w_row)

# ── TAB PETA ────────────────────────────────────────────────────────────────
with tab2:
    st.markdown("### MAPS - Visualisasi Lokasi & Rekomendasi")
    if st.button("Generate Peta", type="primary"):
        with st.spinner("Memuat Peta..."):
            # Titik pusat Jogja
            m = folium.Map(location=[-7.7956, 110.3695], zoom_start=13)
            
            # AMBIL DATA BERDASARKAN MODE
            if MODE_A and hotel_pilih:
                h = df_hotel[df_hotel['NAMA PENGINAPAN'] == hotel_pilih].iloc[0]
                folium.Marker([h['Latitude'], h['Longitude']], popup=hotel_pilih, icon=folium.Icon(color="red", icon="home")).add_to(m)
                hasil_peta = rekomendasi_wisata_dari_hotel(hotel_pilih, bobot_user, budget_maks, kat_pilih, keyword_pilih, 'descending', hari_pilih).head(10)
                for _, row in hasil_peta.iterrows():
                    folium.Marker([row['latitude'], row['longitude']], popup=f"{row['nama']} ({row['jarak_ke_hotel']:.1f} km)", icon=folium.Icon(color="blue", icon="star")).add_to(m)
            
            elif MODE_B and wisata_pilih:
                w = df_wisata_final[df_wisata_final['nama'] == wisata_pilih].iloc[0]
                folium.Marker([w['latitude'], w['longitude']], popup=wisata_pilih, icon=folium.Icon(color="red", icon="flag")).add_to(m)
                hasil_peta = rekomendasi_hotel_dari_wisata(wisata_pilih, bobot_hotel).head(10)
                for _, row in hasil_peta.iterrows():
                    folium.Marker([row['Latitude'], row['Longitude']], popup=f"{row['NAMA PENGINAPAN']} ({row['jarak_ke_wisata']:.1f} km)", icon=folium.Icon(color="blue", icon="bed")).add_to(m)
            
            elif MODE_C:
                hasil_peta = rekomendasi_wisata_global(bobot_wisata_global, kat_pilih, keyword_pilih, budget_min, budget_maks).head(10)
                for _, w in hasil_peta.iterrows():
                    folium.Marker([w['latitude'], w['longitude']], popup=w['nama'], icon=folium.Icon(color="green", icon="star")).add_to(m)

            st_folium(m, width=None, height=500)