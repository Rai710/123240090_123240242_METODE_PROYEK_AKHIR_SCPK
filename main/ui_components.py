# ui_components.py
import streamlit as st
import plotly.graph_objects as go
from streamlit_extras.metric_cards import style_metric_cards

def min_max_scale(val, min_val, max_val, is_cost=False):
    """Fungsi pembantu untuk normalisasi data radar chart"""
    if max_val == min_val: return 100
    if is_cost: return ((max_val - val) / (max_val - min_val)) * 100
    return ((val - min_val) / (max_val - min_val)) * 100

def ui_header():
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🏯 Jogja Tourism SPK")
        st.caption("Sistem Pendukung Keputusan · Metode Weighted Product · Reinnent Rasika Z")
    with col2:
        st.metric("Dataset Hotel", "X hotel")  
        st.metric("Destinasi Wisata", "X tempat") 
def ui_section(text, sub=""):
    """Judul section bawaan Streamlit"""
    st.subheader(text)
    if sub:
        st.caption(sub)

def ui_card_juara(peringkat, kategori, nama, skor, is_hotel=False):
    """Card Juara menggunakan Container dan alert bawaan Streamlit"""
    with st.container(border=True):
        if is_hotel:
            st.warning(f"🏆 **Peringkat {peringkat} | {kategori}**")
        else:
            st.info(f"🏆 **Peringkat {peringkat} | {kategori}**")
            
        st.header(nama)
        st.write(f"**Skor WP:** {skor:.6f}")

def ui_card_paket(index, w_row, hotel_cocok):
    """Card Paket Liburan menggunakan Column dan Container bawaan"""
    bintang_paket = "⭐" * int(hotel_cocok['GOLONGAN_SCORE'])
    
    with st.container(border=True):
        st.subheader(f"🎯 Opsi Paket #{index}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.success(f"**Destinasi Utama:**\n### {w_row['nama']}")
            st.write(f"⭐ Rating: {w_row['vote_average']} | 💰 Tiket: Rp {int(w_row['harga_tiket']):,}")
            
        with col2:
            st.warning(f"**Penginapan Terdekat:**\n### {hotel_cocok['NAMA PENGINAPAN']}")
            st.write(f"📍 Jarak: {hotel_cocok['jarak_ke_wisata']:.2f} km | 🏅 Kelas: {bintang_paket}")

def draw_radar_chart(df_hasil, labels, keys, costs):
    """Membangun Grafik Radar menggunakan Plotly (Python)"""
    max_df, min_df = df_hasil.max(), df_hasil.min()
    fig = go.Figure()
    colors = [("#6359FF", "rgba(99,89,255,0.15)"), ("#00D2A0", "rgba(0,210,160,0.12)")]
    
    for i, (cl, cf) in enumerate(colors):
        if i >= len(df_hasil): break
        row = df_hasil.iloc[i]
        skala = [min_max_scale(row[k], min_df[k], max_df[k], is_cost=costs[idx]) for idx, k in enumerate(keys)]
        
        # PERBAIKAN: Ambil nama berdasarkan jenis data (Wisata atau Hotel)  jadi string
        item_name = row['nama'] if 'nama' in row else row['NAMA PENGINAPAN']
        
        fig.add_trace(go.Scatterpolar(
            r=skala + [skala[0]], theta=labels + [labels[0]],
            fill='toself', fillcolor=cf, line=dict(color=cl, width=2),
            name=f"#{i+1} {str(item_name)[:22]}"
        ))
        
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0,100]),
        ),
        showlegend=True,
        margin=dict(l=40, r=40, t=20, b=40), height=350
    )
    st.plotly_chart(fig, use_container_width=True)