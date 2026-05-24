Tentu, ini adalah draf `README.md` yang profesional, terstruktur, dan informatif untuk proyek Anda. Saya menyusunnya dengan gaya dokumentasi teknis yang disukai dalam proyek akhir atau portofolio.

---

# Jogja Tourism SPK: Sistem Rekomendasi Pariwisata

Sistem Pendukung Keputusan (SPK) untuk rekomendasi destinasi wisata dan akomodasi di Yogyakarta menggunakan metode **Weighted Product (WP)**. Sistem ini dirancang untuk membantu wisatawan dalam merencanakan perjalanan berdasarkan preferensi pribadi, anggaran, dan kedekatan lokasi.

## 🚀 Fitur Utama

* **Mode Rekomendasi Fleksibel**:
* *Sudah Punya Hotel*: Mencari wisata terbaik berdasarkan lokasi menginap saat ini.
* *Belum Punya Hotel*: Mencari hotel terbaik berdasarkan destinasi wisata yang dituju.
* *Paket Liburan*: Meracik kombinasi wisata dan hotel secara otomatis berdasarkan kategori budget (Hemat, Menengah, Eksklusif).


* **Analisis Spasial**: Integrasi algoritma *Haversine* untuk perhitungan jarak geospasial yang akurat antara hotel dan destinasi wisata.
* **Visualisasi Data**: Peta interaktif menggunakan *Folium* dan grafik *Radar Chart* untuk analisis profil destinasi.
* **Dinamis & Responsif**: Bobot kriteria dapat disesuaikan secara *real-time* oleh pengguna.

## 🛠️ Persiapan & Instalasi

### 1. Prasyarat

Pastikan Anda telah menginstal [Python](https://www.python.org/downloads/) (versi 3.9+ disarankan).

### 2. Instalasi Dependensi

Clone repositori ini, lalu jalankan perintah berikut di terminal untuk menginstal pustaka yang diperlukan:

```bash
pip install streamlit pandas numpy plotly folium streamlit-folium streamlit-extras

```

### 3. Struktur Dataset

Sistem membutuhkan dua file CSV utama di dalam direktori `dataset/clean/`:

* `data_hotel_clean.csv`: Berisi data hotel (Nama, Koordinat, Golongan Bintang, Jumlah Kamar).
* `data_wisata_clean.csv`: Berisi data pariwisata (Nama, Koordinat, Rating, Popularitas, Harga Tiket).

*Catatan: Proses pembersihan dataset mentah dilakukan melalui notebook `01_data_preprocessing.ipynb`.*

## 📂 Alur Pemrosesan Data

1. **Eksplorasi (EDA)**: Analisis awal dataset `raw_data.csv` dan `data-hotel.csv` untuk menangani *missing values*.
2. **Pembersihan (Cleaning)**: Menghapus duplikasi, mengisi nilai kosong (*imputation*), dan validasi koordinat GPS agar data layak diolah secara spasial.
3. **Feature Engineering**:
* **Kriteria Jarak**: Menghitung jarak objek wisata ke titik pusat kota (Tugu Jogja) menggunakan *Haversine Formula*.
* **Kriteria Fasilitas (C5)**: Menghitung jumlah hotel dalam radius 3 KM dari setiap destinasi wisata.


4. **Finalisasi**: Transformasi data (mengubah nilai 0 menjadi 0.01) untuk memastikan algoritma *Weighted Product* berjalan tanpa error matematis.

## 🏃 Cara Menjalankan Aplikasi

Setelah instalasi selesai, jalankan perintah berikut di terminal:

```bash
streamlit run app.py

```

Aplikasi akan terbuka secara otomatis di *browser* default Anda (biasanya di `http://localhost:8501`).

## ⚙️ Cara Kerja Metode Weighted Product (WP)

Sistem menggunakan metode WP untuk perangkingan. Keunggulan metode ini adalah penggunaan operasi perkalian untuk menghubungkan atribut kriteria. Bobot kriteria dinormalisasi terlebih dahulu, kemudian setiap alternatif diberi skor berdasarkan pangkat bobot masing-masing, yang menghasilkan keputusan akhir yang lebih stabil dibanding metode aditif sederhana.

## 📝 Kontributor

* **Reinnent Rasika Z**
* **Raihan Buono P**
* *Praktikum Sistem Pendukung Keputusan (SCPK) - Semester 4*

---

