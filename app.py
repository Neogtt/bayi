import streamlit as st
import pandas as pd
import smtplib
import os
import uuid
import datetime
import glob
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from fpdf import FPDF
import tempfile

# ---- Yollar ve yapı ----
ORDERS_PATH = "orders"
os.makedirs(ORDERS_PATH, exist_ok=True)

PUAN_KAYIT_DOSYASI = "puanlar.json"  # bayi puanları burada tutulur

# ---- Puan katsayıları (Ürün Grubu -> katsayı) ----
PUAN_KATSAYILARI = {
    "Kahveler": 3,
    "Şekerleme": 2,
    "Hazır Setler": 2,
    "Soslar": 1
}

# ---- Basit kullanıcılar ----
BAYI_KULLANICILAR = {
    "Paris": "ozturk1234!",
    "Berlin": "Berlin1234!",
    "Hamburg": "Hamburg1234!",
    "Hollanda": "Hollanda1234!",
    "Belcika": "Belcika1234!",
    "Avusturya": "Avusturya1234!",
    "Frankfurt": "Frankfurt1234!",
    "Bremen": "Bremen1234!",
    "Lyon": "Lyon1234!",
    "Romanya": "Romanya1234!",
    "Bulgaristan": "Bulgaristan1234!"
}

# ---- Sheets / Logo ----
sheet_id = "1hXJ9klpaYNz4Ut4l5DCSJnObwGz-ZjCzU0SSmDjzFHE"
LOGO_URL = "https://www.sekeroglugroup.com/storage/settings/xdp5r6DZIFJMNGOStqwvKCiVHDhYxA84jFr61TNp.svg"

gruplar = [
    {"isim": "Kahveler",     "sheet": "Kahveler", "resim": "https://www.sekeroglugroup.com/storage/products/pistachio-coffee_67a9ee6f9f673.png"},
    {"isim": "Hazır Setler", "sheet": "HazirSet", "resim": "https://www.sekeroglugroup.com/storage/products/raw-meatball-sets_67acb5785fe5b.png"},
    {"isim": "Şekerleme",    "sheet": "Sekerleme","resim": "https://www.sekeroglugroup.com/storage/products/mixed-flavoured-suppository-turkish-delight_67acb00828d44.png"},
    {"isim": "Soslar",       "sheet": "Soslar",   "resim": "https://www.sekeroglugroup.com/storage/products/pomegranate-sour_67acb4dc1925c.png"},
]

st.set_page_config(layout="wide")

# ------------------ PUAN FONKSİYONLARI ------------------
def _puan_dosyasi_yukle() -> dict:
    if not os.path.exists(PUAN_KAYIT_DOSYASI):
        return {}
    try:
        with open(PUAN_KAYIT_DOSYASI, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _puan_dosyasi_kaydet(data: dict) -> None:
    with open(PUAN_KAYIT_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_bayi_puan(bayi_adi: str) -> int:
    data = _puan_dosyasi_yukle()
    return int(data.get(bayi_adi, {}).get("toplam_puan", 0))

def add_bayi_puan(bayi_adi: str, eklenecek_puan: int, siparis_kodu: str) -> None:
    data = _puan_dosyasi_yukle()
    bayi_kayit = data.get(bayi_adi, {"toplam_puan": 0, "gecmis": []})
    bayi_kayit["toplam_puan"] = int(bayi_kayit.get("toplam_puan", 0)) + int(eklenecek_puan)
    bayi_kayit["gecmis"].append({
        "siparis_kodu": siparis_kodu,
        "puan": int(eklenecek_puan),
        "tarih": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    data[bayi_adi] = bayi_kayit
    _puan_dosyasi_kaydet(data)

# ------------------ SEPET YEDEKLEME ------------------
def save_cart_to_file(cart, user):
    with open(f"session_{user}.json", "w", encoding="utf-8") as f:
        json.dump(cart, f)

def load_cart_from_file(user):
    try:
        with open(f"session_{user}.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def remove_cart_file(user):
    try:
        os.remove(f"session_{user}.json")
    except:
        pass

# ------------------ STATE ------------------
if "login_ok" not in st.session_state:         st.session_state.login_ok = False
if "bayi_adi" not in st.session_state:         st.session_state.bayi_adi = ""
if "cart" not in st.session_state:             st.session_state.cart = []
if "secili_grup" not in st.session_state:      st.session_state.secili_grup = None
if "show_checkout" not in st.session_state:    st.session_state.show_checkout = False
if "revizyon_siparis" not in st.session_state: st.session_state.revizyon_siparis = None
if "revizyon_loaded" not in st.session_state:  st.session_state.revizyon_loaded = False
if "sepet_duzenlendi" not in st.session_state: st.session_state.sepet_duzenlendi = False

# ------------------ LOGIN ------------------
if not st.session_state.login_ok:
    st.image(LOGO_URL, width=300)
    st.markdown("<h2 style='text-align:center;'>ŞEKEROĞLU SİPARİŞ PORTALI</h2>", unsafe_allow_html=True)
    username = st.text_input("Kullanıcı Adı", max_chars=30)
    password = st.text_input("Şifre", type="password")
    if st.button("Giriş Yap"):
        if username in BAYI_KULLANICILAR and BAYI_KULLANICILAR[username] == password:
            st.session_state.login_ok = True
            st.session_state.bayi_adi = username
            st.success("Giriş başarılı!")
            st.rerun()
        else:
            st.error("Kullanıcı adı veya şifre hatalı!")
    st.stop()

bayi_adi = st.session_state.bayi_adi

# Sidebar: Bayi bilgisi + toplam puan
with st.sidebar:
    st.markdown(f"**Bayi:** {bayi_adi}")
    st.markdown(f"**Toplam Şeker Puan:** {get_bayi_puan(bayi_adi)}")
    if st.button("Çıkış Yap"):
        st.session_state.clear()
        st.rerun()

# Giriş sonrası: sepet taslağı varsa teklif et
if not st.session_state.cart:
    eski_cart = load_cart_from_file(bayi_adi)
    if eski_cart:
        if st.button("💾 Kaydedilmiş sipariş taslağını yükle"):
            st.session_state.cart = eski_cart
            st.success("Taslak siparişiniz geri yüklendi!")
            st.rerun()

# ------------------ ANA MENÜ ------------------
if not st.session_state.show_checkout:
    if st.session_state.secili_grup is None:
        st.markdown(
            f"<div style='display:flex;justify-content:center;align-items:center;margin-bottom:6px;'><img src='{LOGO_URL}' width='400'/></div>",
            unsafe_allow_html=True
        )
        st.markdown("""
            <div style='text-align:center;margin-bottom:32px;margin-top:10px;'>
                <h1 style='color:#b70404;font-weight:900;letter-spacing:2px;font-size:2.3em;'>
                    ŞEKEROĞLU SİPARİŞ EKRANINA HOŞGELDİNİZ!!!
                </h1>
                <p style='font-size:1.1em;margin-bottom:35px;color:#145374;'>Lütfen bir ürün grubu seçiniz:</p>
            </div>
        """, unsafe_allow_html=True)

        cols = st.columns(len(gruplar), gap="large")
        for i, grup in enumerate(gruplar):
            with cols[i]:
                st.markdown(
                    f"""
                    <div style="display:flex;flex-direction:column;align-items:center;">
                        <img src="{grup['resim']}" style="width:140px;height:140px;object-fit:cover;border-radius:16px;border:2px solid #eee;box-shadow:0 2px 9px rgba(140,140,160,0.13);margin-bottom:12px;" />
                        <div style='text-align:center;font-weight:700;font-size:1.18em;margin-top:4px;margin-bottom:10px;'>{grup['isim']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                if st.button("SEÇ", key=f"grup_{grup['isim']}", use_container_width=True):
                    st.session_state.secili_grup = grup["isim"]
                    st.rerun()
        st.stop()

    if st.button("← Ana Ekrana Dön"):
        st.session_state.secili_grup = None
        st.rerun()

    secili_grup = st.session_state.secili_grup
    grup_dict = next(g for g in gruplar if g["isim"] == secili_grup)
    sheet_name = grup_dict["sheet"]

    @st.cache_data(ttl=300)
    def load_sheet(sheet_id: str, sheet_name: str) -> pd.DataFrame:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
        return pd.read_csv(url)

    try:
        df = load_sheet(sheet_id, sheet_name)
    except Exception as e:
        st.error(f"Veri yüklenemedi: {e}")
        st.stop()

    st.markdown(f"<h2 style='margin-top:12px;'>Bayi Sipariş Ekranı — {secili_grup}</h2>", unsafe_allow_html=True)

    # Yatay grup menüsü
    grup_cols = st.columns(len(gruplar), gap="medium")
    for i, grup in enumerate(gruplar):
        with grup_cols[i]:
            st.markdown(
                f"""<div style='text-align:center;'>
                    <img src="{grup['resim']}" style="width:38px;height:38px;object-fit:cover;border-radius:10px;vertical-align:middle;margin-bottom:4px;" />
                    <br>
                    <span style="font-size:1.03em; font-weight:{'700' if grup['isim']==secili_grup else '500'}; color:{'#b70404' if grup['isim']==secili_grup else '#223'}">
                        {grup['isim']}
                    </span>
                </div>""",
                unsafe_allow_html=True
            )
            if st.button("Git", key=f"grup_goto_{grup['isim']}", use_container_width=True, disabled=grup["isim"]==secili_grup):
                st.session_state.secili_grup = grup["isim"]
                st.rerun()

    # Sabit checkout butonu
    st.markdown("""
        <style>
        .checkout-fab { position: fixed; bottom: 38px; right: 54px; z-index: 9999; }
        </style>
    """, unsafe_allow_html=True)
    st.markdown("<div class='checkout-fab'>", unsafe_allow_html=True)
    if st.button("🛒 TIR'ıma Git", key="fab_checkout"):
        st.session_state.show_checkout = True
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # Ürünler
    N_COL = max(1, min(4, len(df)))
    urunler = [df.iloc[i:i+N_COL] for i in range(0, len(df), N_COL)]
    for row_items in urunler:
        cols = st.columns(N_COL, gap="large")
        for idx, (i, row) in enumerate(row_items.iterrows()):
            with cols[idx]:
                with st.container(border=True):
                    img_link = row.get("Görsel Linki", "")
                    if isinstance(img_link, str) and img_link.startswith("http"):
                        st.image(img_link, width=155)
                    else:
                        st.warning("Görsel bulunamadı.")

                    st.markdown(f"<div style='font-weight:700;font-size:1.12em;margin-top:4px;'>{row['Ürün Adı']}</div>", unsafe_allow_html=True)
                    st.write(
                        f"Koli İçi: {row['Koli İçi Adet']}  \n"
                        f"Adet Fiyatı: {row['Adet Fiyatı (€)']} €  \n"
                        f"Koli Fiyatı: {row['Koli Fiyatı (€)']} €  \n"
                        f"Palet Üstü Koli: {row['Palet Üstü Koli']}"
                    )

                    siparis_tipi = st.radio(
                        f"{row['Ürün Adı']} için sipariş tipi",
                        ("Koli", "Palet"),
                        key=f"tip_{i}_{secili_grup}",
                        horizontal=True,
                        label_visibility="collapsed"
                    )

                    if siparis_tipi == "Koli":
                        qty = st.number_input("Koli", min_value=0, step=1, key=f"qty_{i}_{secili_grup}")
                    else:
                        try:
                            palet_ustu_koli = int(float(str(row["Palet Üstü Koli"]).replace(",", ".").strip()))
                        except Exception:
                            palet_ustu_koli = 1
                        palet_adedi = st.number_input("Palet Adedi", min_value=0, step=1, key=f"paletqty_{i}_{secili_grup}")
                        qty = palet_adedi * palet_ustu_koli
                        st.caption(f"{palet_adedi} palet × {palet_ustu_koli} koli/palet = {qty} koli")

                    st.markdown("<div style='margin-top:18px;'></div>", unsafe_allow_html=True)
                    if st.button("🚚 TIR'a Ekle", key=f"add_{i}_{secili_grup}"):
                        if qty > 0:
                            try:
                                koli_fiyat = float(str(row["Koli Fiyatı (€)"]).replace(",", ".").strip())
                            except:
                                koli_fiyat = 0
                            st.session_state.cart.append({
                                "Ürün Grubu": secili_grup,
                                "Ürün Adı": row["Ürün Adı"],
                                "Koli Adedi": qty,
                                "Koli Fiyatı (€)": koli_fiyat,
                                "Toplam (€)": qty * koli_fiyat,
                                "Palet Üstü Koli": row.get("Palet Üstü Koli", 1)
                            })
                            save_cart_to_file(st.session_state.cart, bayi_adi)
                            st.success("Ürün TIR'a eklendi.")
                        else:
                            st.warning("Lütfen koli/palet adedi girin.")

# ------------------ CHECKOUT ------------------
if st.session_state.show_checkout:
    st.header("TIR Kontrol Ekranı (Checkout)")

    # Eski siparişleri tarama
    eski_siparisler = []
    for file in sorted(glob.glob(f"{ORDERS_PATH}/*.xlsx"), reverse=True):
        kod = os.path.basename(file).replace(".xlsx", "")
        try:
            df_ = pd.read_excel(file)
            bayi_ad = kod.split("_")[-1]
            tarih = "-"
            if kod.startswith("SP-") and len(kod.split("-")) > 1:
                tarih_kod = kod.split("-")[1]
                try:
                    tarih = datetime.datetime.strptime(tarih_kod, "%Y%m%d").strftime("%d.%m.%Y")
                except Exception:
                    tarih = "-"
            eski_siparisler.append((kod, bayi_ad, file, df_, tarih))
        except Exception:
            continue

    eski_opsiyonlar = [f"{kod} ({bayi_ad}) [{tarih}]" for kod, bayi_ad, file, df_, tarih in eski_siparisler if bayi_ad == bayi_adi]
    eski_kod_map   = {f"{kod} ({bayi_ad}) [{tarih}]": file for kod, bayi_ad, file, df_, tarih in eski_siparisler if bayi_ad == bayi_adi}

    st.markdown("##### Eski Siparişe Git / Revize Et:")
    eski_secim = st.selectbox("Geçmiş siparişlerinizden birini yükleyin:", ["Seçiniz"] + eski_opsiyonlar, key="revize_combo")

    if eski_secim != "Seçiniz":
        dosya = eski_kod_map[eski_secim]
        df_loaded = pd.read_excel(dosya)
        st.markdown(f"**Seçili Sipariş:** {eski_secim}")
        st.dataframe(df_loaded, use_container_width=True)
        if st.button("TIR'a Aktar ve Düzenle"):
            st.session_state.cart = df_loaded.to_dict(orient="records")
            st.session_state.revizyon_siparis = os.path.splitext(os.path.basename(dosya))[0]
            st.session_state.revizyon_loaded = True
            st.session_state.sepet_duzenlendi = True
            save_cart_to_file(st.session_state.cart, bayi_adi)
            st.rerun()

    cart = st.session_state.cart
    summary = pd.DataFrame(cart)

    # Toplam palet ve Şeker Puan hesapları
    toplam, toplam_palet, toplam_seker_puan = 0.0, 0.0, 0

    if not summary.empty and "Koli Adedi" in summary.columns and "Palet Üstü Koli" in summary.columns:
        # Toplam Palet
        summary["Toplam Palet"] = summary.apply(
            lambda r: round(float(r["Koli Adedi"]) / float(str(r.get("Palet Üstü Koli", 1)).replace(",", ".")), 2)
            if float(str(r.get("Palet Üstü Koli", 1)).replace(",", ".")) > 0 else 0, axis=1
        )

        # Şeker Puan (satır bazında)
        def satir_puan_hesapla(r):
            grup = str(r.get("Ürün Grubu", "")).strip()
            katsayi = PUAN_KATSAYILARI.get(grup, 1)
            try:
                tutar = float(r.get("Toplam (€)", 0))
            except Exception:
                tutar = 0.0
            return int(round(tutar * katsayi))

        summary["Şeker Puan"] = summary.apply(satir_puan_hesapla, axis=1)

        # Alt toplamlar
        try:
            toplam = summary["Toplam (€)"].astype(float).sum()
        except Exception:
            toplam = float(sum([float(str(x).replace(",", ".")) for x in summary["Toplam (€)"].tolist()]))

        toplam_palet = float(summary["Toplam Palet"].sum())
        toplam_seker_puan = int(summary["Şeker Puan"].sum())

        # Tabloda göster
        st.table(summary)

        # ---- ÖZET METRİKLER ----
        c1, c2, c3 = st.columns(3)
        c1.metric("Genel Toplam (€)", f"{toplam:,.2f}")
        c2.metric("Toplam Palet", f"{toplam_palet:.2f}")
        c3.metric("Toplam Şeker Puan", f"{toplam_seker_puan:,}")

        # Yükleme tipi
        yukleme_tipi = st.radio(
            "Yükleme Biçimi Seçiniz",
            options=["TIR (33 Palet)", "Konteynır (40'lık, 24 Palet)", "Konteynır (20'lik, 11 Palet)"],
            index=0,
            horizontal=True
        )
        if yukleme_tipi.startswith("TIR"):
            max_palet = 33
        elif "40" in yukleme_tipi:
            max_palet = 24
        elif "20" in yukleme_tipi:
            max_palet = 11
        else:
            max_palet = 33

        kalan_palet = max(0, max_palet - toplam_palet)

        st.markdown(f"""
            <div style='font-size:1.12em; font-weight:bold; color:#215; margin:10px 0 6px 0;'>
              Şu anda sepette <span style="color:#b70404;">{toplam_palet:.2f} palet</span> var. <br>
              <span style="color:#3a79dd;">Tam {max_palet} palet</span> için 
              <span style="color:#b7a004;">{kalan_palet:.2f} palet</span> yer kaldı. <br>
              Toplam Şeker Puan: <span style="color:#b7046d;">{toplam_seker_puan:,}</span>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.table(pd.DataFrame(columns=[
            "Ürün Grubu", "Ürün Adı", "Koli Adedi", "Koli Fiyatı (€)", "Toplam (€)", "Toplam Palet", "Şeker Puan"
        ]))
        st.info("Henüz TIR'ınızda ürün yok.")

    # PDF oluşturma
    def pdf_siparis_olustur(summary, bayi_adi, tarih_str):
        # Font dosyaları repo kökünde olmalı
        FONT_REG = os.path.join(os.path.dirname(__file__), "DejaVuSans.ttf")
        FONT_BLD = os.path.join(os.path.dirname(__file__), "DejaVuSans-Bold.ttf")

        pdf = FPDF()
        pdf.add_page()
        pdf.add_font("DejaVu", "", FONT_REG, uni=True)
        pdf.add_font("DejaVu", "B", FONT_BLD, uni=True)

        pdf.set_font("DejaVu", "", 14)
        pdf.cell(0, 9, "ŞEKEROĞLU SİPARİŞ", 0, 1, 'C')
        pdf.set_font("DejaVu", "", 7)
        pdf.cell(0, 5, f"Tarih: {tarih_str}", 0, 1, 'R')
        pdf.cell(0, 5, f"Siparişi Veren Bayi: {bayi_adi}", 0, 1, 'L')
        pdf.ln(2)
        pdf.set_font("DejaVu", "B", 7)
        cols = ["Grup", "Ürün", "Koli", "Fiyat", "Tutar", "Palet", "Puan"]
        widths = [17,   50,     12,     16,      17,      12,      12]
        for col, w in zip(cols, widths):
            pdf.cell(w, 5, col, border=1, align="C")
        pdf.ln()
        pdf.set_font("DejaVu", "", 7)
        for _, r in summary.iterrows():
            pdf.cell(widths[0], 5, str(r.get("Ürün Grubu", ""))[:14], border=1)
            pdf.cell(widths[1], 5, str(r.get("Ürün Adı", ""))[:30],  border=1)
            pdf.cell(widths[2], 5, str(r.get("Koli Adedi", "")),     border=1, align="C")
            pdf.cell(widths[3], 5, str(r.get("Koli Fiyatı (€)", "")),border=1, align="R")
            pdf.cell(widths[4], 5, str(r.get("Toplam (€)", "")),     border=1, align="R")
            pdf.cell(widths[5], 5, str(r.get("Toplam Palet", "")),   border=1, align="C")
            pdf.cell(widths[6], 5, str(r.get("Şeker Puan", "")),     border=1, align="C")
            pdf.ln()
        pdf.ln(6)
        pdf.set_font("DejaVu", "", 8)
        pdf.cell(65, 5, "Siparişi Veren:", 0, 0, 'L')
        pdf.cell(65, 5, "Yönetici Onayı:", 0, 1, 'L')
        pdf.cell(65, 9, "", 1, 0, 'L')
        pdf.cell(65, 9, "", 1, 1, 'L')
        return pdf

    if not summary.empty and "Toplam (€)" in summary.columns:
        pdf_tarih = datetime.datetime.now().strftime("%d.%m.%Y")
        if st.button("📄 PDF Çıktısı Al"):
            pdf = pdf_siparis_olustur(summary, bayi_adi, pdf_tarih)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                pdf.output(tmp_file.name)
                with open(tmp_file.name, "rb") as f:
                    st.download_button(
                        label="PDF İndir",
                        data=f.read(),
                        file_name=f"Siparis_{bayi_adi}_{pdf_tarih.replace('.', '-')}.pdf",
                        mime="application/pdf"
                    )

    # Sepetten ürün çıkarma
    if not summary.empty and "Toplam (€)" in summary.columns:
        for sidx, row in summary.iterrows():
            if st.button(f"❌ {row['Ürün Adı']} ürünü çıkar", key=f"del_checkout_{sidx}"):
                st.session_state.cart.pop(sidx)
                save_cart_to_file(st.session_state.cart, bayi_adi)
                st.rerun()

        # SİPARİŞİ ONAYLA → puanı ekle + e-posta gönder
        if st.button("Siparişi Onayla"):
            if st.session_state.revizyon_siparis:
                siparis_kodu = st.session_state.revizyon_siparis + "-REV"
                konu_etiketi = "REVİZE SİPARİŞ"
            else:
                siparis_kodu = f"SP-{datetime.datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}_{bayi_adi}"
                konu_etiketi = "YENİ SİPARİŞ"

            # Excel kaydet
            filepath = f"{ORDERS_PATH}/{siparis_kodu}.xlsx"
            summary.to_excel(filepath, index=False)

            # Puan ekle (kalıcı)
            add_bayi_puan(bayi_adi, toplam_seker_puan, siparis_kodu)

            # Mail gövdesi
            mail_body = f"""
Merhaba,

Siparişi veren bayi: {bayi_adi}
Sipariş Kodu: {siparis_kodu}

{'Daha önce gönderdiğiniz sipariş üzerinde değişiklik yapılmıştır.' if konu_etiketi=="REVİZE SİPARİŞ" else 'Yeni sipariş oluşturuldu.'}

Sipariş özeti ektedir.

Genel Toplam: {toplam:.2f} €
Toplam Palet: {toplam_palet:.2f}
Toplam Şeker Puan: {toplam_seker_puan:,}

İyi Çalışmalar!
"""

            msg = MIMEMultipart()
            msg['From'] = "todo@sekeroglugroup.com"
            msg['To'] = "export1@sekeroglugroup.com, kemal.ilker27@gmail.com"
            msg['Subject'] = f"{konu_etiketi} - {bayi_adi} - Sipariş Kodu: {siparis_kodu}"
            msg.attach(MIMEText(mail_body, 'plain'))
            with open(filepath, "rb") as file:
                part = MIMEApplication(file.read(), Name="bayi_siparisi.xlsx")
                part['Content-Disposition'] = 'attachment; filename=\"bayi_siparisi.xlsx\"'
                msg.attach(part)

            try:
                # Prod için secrets kullanmanı öneririm.
                smtp_server = "smtp.gmail.com"
                smtp_port = 587
                smtp_user = "todo@sekeroglugroup.com"
                smtp_pass = "prfq lwme tjgm eusp"

                server = smtplib.SMTP(smtp_server, smtp_port)
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(msg['From'], [a.strip() for a in msg['To'].split(",")], msg.as_string())
                server.quit()

                st.success(f"Siparişiniz gönderildi! Sipariş Kodu: {siparis_kodu}")
                st.info(f"Güncel Toplam Şeker Puanınız: {get_bayi_puan(bayi_adi)}")

                # sepet temizliği
                st.session_state.cart = []
                remove_cart_file(bayi_adi)
                st.session_state.show_checkout = False
                st.session_state.revizyon_siparis = None
                st.session_state.revizyon_loaded = False
                st.rerun()
            except Exception as e:
                st.error(f"E-posta gönderilemedi! Hata: {e}")

    # Bilgilendirme
    if st.session_state.get("sepet_duzenlendi", False):
        st.success("Sipariş TIR'a eklendi ve düzenlenebilir!")
        st.session_state.sepet_duzenlendi = False

    if st.button("← Alışverişe Devam Et"):
        st.session_state.show_checkout = False
        st.rerun()
