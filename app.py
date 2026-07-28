"""
app.py
------
"İndirim Fırsatı" - Streamlit Kontrol Paneli
Telefondan (veya herhangi bir tarayıcıdan) yönetilebilecek, mobil uyumlu
e-ticaret indirim takip sistemi arayüzü.

Çalıştırmak için (lokal):
    streamlit run app.py

Streamlit Community Cloud'a yayınlamak için:
    1) Bu klasörü bir GitHub reposuna yükle (app.py, scraper.py,
       price_analyzer.py, email_sender.py, requirements.txt).
    2) share.streamlit.io üzerinden "New app" ile repoyu bağla, main file
       olarak app.py'yi seç.
    3) App Settings -> Secrets kısmına şunu ekle:
         GMAIL_USER = "senin_mailin@gmail.com"
         GMAIL_APP_PASSWORD = "16-haneli-uygulama-sifresi"
"""

import json
import os
import streamlit as st

from scraper import CATEGORIES, simulate_scrape, real_scrape_multi_site
from real_scrapers import SITE_SCRAPERS
from price_analyzer import analyze_products
from email_sender import build_html_email, send_email

CONFIG_PATH = "config.json"

DEFAULT_CONFIG = {
    "categories": ["Telefon", "Laptop"],
    "min_discount_pct": 15,
    "min_rating": 4.0,
    "history_days": 90,
    "max_products": 10,
    "email": "",
    "data_source": "Simülasyon",
    "sites": list(SITE_SCRAPERS.keys()),
}

st.set_page_config(
    page_title="İndirim Fırsatı",
    page_icon="🔥",
    layout="centered",  # mobilde daha rahat okunur
    initial_sidebar_state="collapsed",
)

# --- Mobil dostu küçük CSS dokunuşları ---
st.markdown("""
<style>
    .block-container {padding-top: 1.2rem; padding-bottom: 3rem; max-width: 720px;}
    div[data-testid="stMetricValue"] {font-size: 1.3rem;}
    .deal-card {
        background: #ffffff; border: 1px solid #eee; border-radius: 14px;
        padding: 14px; margin-bottom: 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.05);
    }
    .deal-title {font-weight: 700; font-size: 15px; color: #1a1a2e;}
    .deal-meta {font-size: 12px; color: #888; margin-bottom: 6px;}
    .old-price {text-decoration: line-through; color: #aaa; font-size: 13px;}
    .discount-badge {
        background: #e8f9ee; color: #1e9e5a; font-weight: 700; font-size: 12px;
        padding: 2px 8px; border-radius: 20px; margin-left: 6px;
    }
    .new-price {font-size: 20px; font-weight: 800; color: #e63946;}
</style>
""", unsafe_allow_html=True)


def load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except Exception:
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()


def save_config(cfg: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


if "config" not in st.session_state:
    st.session_state.config = load_config()

if "deals" not in st.session_state:
    st.session_state.deals = []


st.title("🔥 İndirim Fırsatı")
st.caption("Kategori bazlı akıllı indirim takip sistemi — sahte indirimler otomatik elenir.")

tab_settings, tab_scan, tab_about = st.tabs(["⚙️ Ayarlar", "🔍 Tarama & Sonuçlar", "ℹ️ Nasıl Çalışır"])

# ---------------------------------------------------------------------------
# AYARLAR SEKMESİ
# ---------------------------------------------------------------------------
with tab_settings:
    cfg = st.session_state.config

    st.subheader("Takip Edilecek Kategoriler")
    categories = st.multiselect(
        "Kategori seç",
        options=CATEGORIES,
        default=[c for c in cfg["categories"] if c in CATEGORIES],
        label_visibility="collapsed",
    )

    st.subheader("Veri Kaynağı")
    data_source = st.radio(
        "Ürünler nereden taransın?",
        options=["Simülasyon", "Gerçek Kazıma"],
        index=0 if cfg.get("data_source", "Simülasyon") == "Simülasyon" else 1,
        horizontal=True,
        label_visibility="collapsed",
    )
    selected_sites = cfg.get("sites", list(SITE_SCRAPERS.keys()))
    if data_source == "Gerçek Kazıma":
        selected_sites = st.multiselect(
            "Hangi sitelerde arasın?",
            options=list(SITE_SCRAPERS.keys()),
            default=[s for s in cfg.get("sites", list(SITE_SCRAPERS.keys())) if s in SITE_SCRAPERS],
        )
        st.caption(
            "⚠️ Gerçek kazıma modunda siteler zaman zaman istek engelleyebilir "
            "(özellikle Amazon). Ayrıca 'sahte indirim' tespiti için fiyat geçmişinin "
            "birkaç gün/hafta birikmesi gerekir — ilk taramalarda çoğu ürün "
            "'yetersiz geçmiş' nedeniyle listelenmeyebilir, bu normaldir."
        )

    st.subheader("Filtreler")
    col1, col2 = st.columns(2)
    with col1:
        min_discount = st.slider("Minimum İndirim Oranı (%)", 5, 70, int(cfg["min_discount_pct"]), step=5)
    with col2:
        min_rating = st.slider("Minimum Ürün Puanı", 3.0, 5.0, float(cfg["min_rating"]), step=0.1)

    col3, col4 = st.columns(2)
    with col3:
        history_days = st.selectbox(
            "Fiyat Geçmişi Analiz Süresi",
            options=[30, 60, 90],
            index=[30, 60, 90].index(cfg["history_days"]) if cfg["history_days"] in [30, 60, 90] else 2,
            format_func=lambda x: f"Son {x} gün",
        )
    with col4:
        max_products = st.number_input("Rapordaki Maksimum Ürün Sayısı", min_value=1, max_value=50, value=int(cfg["max_products"]))

    st.subheader("Bildirim E-postası")
    email = st.text_input("E-posta adresin (rapor buraya gönderilecek)", value=cfg["email"], placeholder="ornek@gmail.com")

    if st.button("💾 Ayarları Kaydet", use_container_width=True, type="primary"):
        new_cfg = {
            "categories": categories,
            "min_discount_pct": min_discount,
            "min_rating": min_rating,
            "history_days": history_days,
            "max_products": max_products,
            "email": email,
            "data_source": data_source,
            "sites": selected_sites,
        }
        save_config(new_cfg)
        st.session_state.config = new_cfg
        st.success("Ayarlar config.json dosyasına kaydedildi ✅")

    st.info(
        "🔒 Gmail şifresi güvenlik nedeniyle config.json'a değil, "
        "Streamlit **Secrets** bölümüne kaydedilmelidir (Ayarlar sekmesinde "
        "sadece hedef e-posta adresi tutulur).",
        icon="🔒",
    )

# ---------------------------------------------------------------------------
# TARAMA & SONUÇLAR SEKMESİ
# ---------------------------------------------------------------------------
with tab_scan:
    cfg = st.session_state.config

    if not cfg["categories"]:
        st.warning("Önce **Ayarlar** sekmesinden en az bir kategori seçip kaydet.")
    else:
        st.write(f"Seçili kategoriler: **{', '.join(cfg['categories'])}**")

        if st.button("🔍 Taramayı Başlat", use_container_width=True, type="primary"):
            spinner_msg = (
                "Gerçek sitelerde aranıyor (bu biraz sürebilir)..."
                if cfg.get("data_source") == "Gerçek Kazıma"
                else "Ürünler taranıyor ve fiyat geçmişi analiz ediliyor..."
            )
            with st.spinner(spinner_msg):
                diagnostics = None
                if cfg.get("data_source") == "Gerçek Kazıma":
                    products, diagnostics = real_scrape_multi_site(cfg["categories"], sites=cfg.get("sites"))
                else:
                    products = simulate_scrape(cfg["categories"], history_days=cfg["history_days"])

                st.session_state.raw_product_count = len(products)
                st.session_state.raw_products_sample = [
                    (p.name, p.source, p.current_price, len(p.price_history)) for p in products[:6]
                ]
                st.session_state.scrape_diagnostics = diagnostics

                deals = analyze_products(
                    products,
                    min_discount_pct=cfg["min_discount_pct"],
                    min_rating=cfg["min_rating"],
                    history_days=cfg["history_days"],
                    max_results=cfg["max_products"],
                )
                st.session_state.deals = deals
            st.success(f"{len(deals)} gerçek indirim fırsatı bulundu.")

            with st.expander(f"🔧 Teknik detay: taramada toplam {st.session_state.get('raw_product_count', 0)} ürün bulundu"):
                diag_list = st.session_state.get("scrape_diagnostics")
                if diag_list:
                    st.write("**Site bazlı sonuçlar (HTTP durum kodu / bulunan kart sayısı):**")
                    for d in diag_list:
                        site = d.get("site", "?")
                        cat = d.get("category", "?")
                        status = d.get("status_code", "yok")
                        cards = d.get("cards_found", "-")
                        found = d.get("items_found", 0)
                        blocked = " 🚫 engellenmiş görünüyor" if d.get("blocked") else ""
                        err = f" — hata: {d.get('error')}" if d.get("error") else ""
                        st.write(f"- **{site}** / {cat}: HTTP {status}, {cards} kart bulundu, {found} ürün alındı{blocked}{err}")

                    sample_diag = next((d for d in diag_list if d.get("sample_html")), None)
                    if sample_diag:
                        st.write("---")
                        page_title = sample_diag.get("page_title")
                        title_info = f" (sayfa başlığı: *{page_title}*)" if page_title else ""
                        st.write(
                            f"**{sample_diag.get('site')}** beklenenden farklı bir sayfa döndürdü{title_info}. "
                            "Aşağıdaki ham HTML/örnek metni kopyalayıp bana gönderirsen, "
                            "neyin değiştiğini görüp düzeltebilirim:"
                        )
                        st.code(sample_diag["sample_html"], language="html")
                    st.caption(
                        "HTTP 200 ama 'kart bulundu: 0' ise → sitenin HTML yapısı değişmiş, "
                        "seçicilerin güncellenmesi gerekiyor. HTTP 403/429/yok ise → site isteği "
                        "muhtemelen engellemiş."
                    )

                if st.session_state.get("raw_product_count", 0) == 0:
                    st.write(
                        "Siteler hiç ürün döndürmedi. Yukarıdaki tabloya bakarak hangi "
                        "sitenin engellendiğini mi yoksa seçicilerin mi güncel olmadığını "
                        "görebilirsin."
                    )
                else:
                    st.write("Örnek bulunan ürünler (ilk 6):")
                    for name, source, price, hist_len in st.session_state.get("raw_products_sample", []):
                        st.write(f"- **{name}** ({source}) — {price} TL — {hist_len} günlük fiyat geçmişi")
                    st.caption(
                        "Fiyat geçmişi az olan ürünler (5 günden az), sahte indirim "
                        "riskine karşı henüz 'gerçek fırsat' sayılmıyor — bu normaldir, "
                        "sistem birkaç gün/hafta çalıştıkça artacaktır."
                    )

        deals = st.session_state.deals
        if deals:
            for d in deals:
                p = d.product
                rating_txt = f"⭐ {p.rating}/5" if p.rating is not None else "puan yok"
                source_txt = f"{p.source} • " if getattr(p, "source", "") else ""
                st.markdown(f"""
                <div class="deal-card">
                    <div class="deal-title">{p.name}</div>
                    <div class="deal-meta">{source_txt}{p.category} • {rating_txt}</div>
                    <span class="old-price">{p.original_price:,.2f} TL</span>
                    <span class="discount-badge">-%{d.discount_pct:.0f}</span>
                    <div class="new-price">{p.current_price:,.2f} TL</div>
                </div>
                """, unsafe_allow_html=True)

            st.divider()
            st.subheader("📧 Raporu E-posta ile Gönder")

            if not cfg["email"]:
                st.warning("Önce Ayarlar sekmesinden e-posta adresini kaydet.")
            else:
                gmail_user = st.secrets.get("GMAIL_USER", "")
                gmail_pass = st.secrets.get("GMAIL_APP_PASSWORD", "")

                if not gmail_user or not gmail_pass:
                    st.error(
                        "Gönderici Gmail bilgileri bulunamadı. Streamlit Secrets kısmına "
                        "GMAIL_USER ve GMAIL_APP_PASSWORD ekle."
                    )
                else:
                    if st.button(f"✉️ {cfg['email']} adresine gönder", use_container_width=True):
                        html = build_html_email(deals)
                        with st.spinner("E-posta gönderiliyor..."):
                            ok, msg = send_email(
                                to_email=cfg["email"],
                                gmail_user=gmail_user,
                                gmail_app_password=gmail_pass,
                                subject=f"🔥 {len(deals)} yeni indirim fırsatı bulundu!",
                                html_content=html,
                            )
                        if ok:
                            st.success("E-posta başarıyla gönderildi ✅")
                        else:
                            st.error(f"E-posta gönderilemedi: {msg}")
        elif "deals" in st.session_state:
            st.caption("Henüz tarama yapılmadı ya da filtrelere uyan gerçek indirim bulunamadı.")

# ---------------------------------------------------------------------------
# BİLGİ SEKMESİ
# ---------------------------------------------------------------------------
with tab_about:
    st.markdown("""
### Sistem nasıl çalışır?

1. **Ayarlar**: Takip etmek istediğin kategorileri ve filtreleri belirleyip
   kaydediyorsun (`config.json`).
2. **Tarama**: Sistem, seçilen kategorilerdeki ürünleri tarar (bu demo
   sürümde gerçekçi sentetik veriyle simüle edilir; `scraper.py` içindeki
   `real_scrape()` fonksiyonunu doldurarak gerçek bir siteye bağlayabilirsin).
3. **Sahte İndirim Filtresi**: Her ürünün fiyat geçmişi incelenir. Fiyatı
   önce yükseltip sonra "indirim" adı altında eski seviyesine çekilmiş
   ürünler otomatik elenir.
4. **Gerçek Fırsatlar**: Sadece seçtiğin analiz süresinin (30/60/90 gün)
   en düşük fiyatına sahip ve filtrelerine uyan ürünler listelenir.
5. **E-posta Raporu**: Beğendiğin an, bulunan fırsatları tek tıkla şık bir
   HTML e-posta olarak Gmail adresine gönderebilirsin.

### Otomatik / zamanlanmış çalıştırma
Streamlit Community Cloud kendi başına zamanlanmış (cron) görev çalıştırmaz;
uygulama sadece sen açtığında/ziyaret edildiğinde aktif olur. Telefonuna
otomatik e-posta gelmesini istiyorsan, `scheduled_task.py` dosyasını ve
GitHub Actions cron kurulumunu kullanabilirsin (README.md içinde anlatılmıştır).
""")
