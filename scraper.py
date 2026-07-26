"""
scraper.py
----------
"İndirim Fırsatı" sisteminin veri toplama katmanı.

Bu modül iki modda çalışabilir:
1) SIMULASYON MODU (varsayılan, demo/test için):
   Gerçekçi fiyat geçmişleri ile sahte ürün verisi üretir. Streamlit Community
   Cloud üzerinde canlıya alırken hiçbir siteye istek atmadan sistemin uçtan
   uca çalıştığını görebilmen için buradadır.

2) GERÇEK KAZIMA MODU (real_scrape=True):
   requests + BeautifulSoup ile gerçek bir e-ticaret sitesinden veri çeker.
   Her sitenin HTML yapısı farklı olduğundan (ve zamanla değiştiğinden)
   `_scrape_site_template` fonksiyonu bir ŞABLON olarak bırakılmıştır.
   Kullanmak istediğin siteye (örn. kendi mağazan, bir API sağlayan site,
   veya scraping izni olan bir site) göre CSS seçicilerini burada
   güncellemen gerekir.

   ÖNEMLİ / YASAL UYARI:
   Çoğu büyük e-ticaret sitesinin (Trendyol, Hepsiburada, Amazon vb.)
   kullanım şartları otomatik veri kazımayı yasaklar veya kısıtlar ve
   IP engellemesi uygulayabilirler. Bu şablonu yalnızca kazımaya izin
   veren siteler, kendi API'niz veya kendi sitenizle kullanman önerilir.
   Sorumluluk kullanıcıya aittir.
"""

from __future__ import annotations
import random
import datetime as dt
from dataclasses import dataclass, field
from typing import List, Dict
import requests
from bs4 import BeautifulSoup


CATEGORIES = [
    "Tablet", "Telefon", "Laptop", "Kamera",
    "Video Ekipmanları", "Ev Ürünleri", "Kulaklık", "Akıllı Saat"
]

_SAMPLE_PRODUCTS = {
    "Tablet": ["Galaxy Tab A9", "iPad 10. Nesil", "Lenovo Tab M10", "Xiaomi Pad 6"],
    "Telefon": ["iPhone 14", "Galaxy S23", "Xiaomi 13T", "Redmi Note 13 Pro"],
    "Laptop": ["MacBook Air M2", "ASUS Vivobook 15", "Lenovo IdeaPad 3", "HP Pavilion 14"],
    "Kamera": ["Canon EOS M50", "Sony Alpha A6000", "Nikon Z30", "GoPro Hero 12"],
    "Video Ekipmanları": ["DJI Osmo Pocket 3", "Rode NT-USB Mikrofon", "Ring Light 45cm", "Gimbal Zhiyun Smooth 5"],
    "Ev Ürünleri": ["Robot Süpürge Xiaomi", "Airfryer Philips", "Su Isıtıcı Fakir", "Blender Set"],
    "Kulaklık": ["AirPods Pro 2", "Sony WH-1000XM5", "JBL Tune 720BT", "Samsung Galaxy Buds2"],
    "Akıllı Saat": ["Apple Watch SE", "Galaxy Watch 6", "Xiaomi Mi Band 8", "Amazfit GTS 4"],
}


@dataclass
class Product:
    name: str
    category: str
    url: str
    image_url: str
    rating: float | None
    current_price: float
    original_price: float  # sitede gösterilen "eski fiyat" / liste fiyatı
    price_history: List[Dict] = field(default_factory=list)  # [{"date": "YYYY-MM-DD", "price": float}, ...]
    source: str = ""  # hangi siteden geldiği (Trendyol, Amazon, vb.) - gerçek modda dolu

    @property
    def discount_pct(self) -> float:
        if self.original_price <= 0:
            return 0.0
        return round((self.original_price - self.current_price) / self.original_price * 100, 1)


def _generate_price_history(base_price: float, days: int, fake_discount: bool) -> List[Dict]:
    """Belirli gün sayısı için sentetik fiyat geçmişi üretir.

    fake_discount=True ise: fiyat son günlerde suni olarak yükseltilip
    hemen ardından düşürülmüş gibi bir örüntü oluşturur (sahte indirim testi için).
    """
    today = dt.date.today()
    history = []
    price = base_price

    if fake_discount:
        # Çoğu gün stabil, son 5-10 gün içinde fiyat %20-40 artırılıp
        # hemen indirim gününde tekrar düşürülüyor (klasik "önce zam sonra indirim").
        hike_start = random.randint(5, 10)
        for i in range(days, 0, -1):
            if i == hike_start:
                price = base_price * random.uniform(1.2, 1.4)
            elif i < hike_start and i > 1:
                price = price  # zamlı fiyat sabit kalıyor
            elif i == 1:
                price = base_price  # "indirim" aslında sadece eski fiyata dönüş
            history.append({"date": str(today - dt.timedelta(days=i)), "price": round(price, 2)})
        history.append({"date": str(today), "price": round(base_price, 2)})
    else:
        # Gerçek indirim: fiyat zaman içinde küçük dalgalanmalarla düşüyor,
        # bugünkü fiyat son N günün en düşüğü.
        price = base_price * random.uniform(1.05, 1.25)
        for i in range(days, 0, -1):
            drift = random.uniform(-0.01, 0.015)
            price = max(base_price * 0.95, price * (1 + drift))
            history.append({"date": str(today - dt.timedelta(days=i)), "price": round(price, 2)})
        history.append({"date": str(today), "price": round(base_price, 2)})

    return history


def simulate_scrape(categories: List[str], history_days: int = 90, seed: int | None = None) -> List[Product]:
    """Seçilen kategoriler için sentetik ama gerçekçi ürün + fiyat geçmişi üretir.

    Ürünlerin bir kısmı bilinçli olarak "sahte indirim" örüntüsüyle üretilir,
    böylece price_analyzer.py'nin bunları elediğini test edebilirsin.
    """
    if seed is not None:
        random.seed(seed)

    products: List[Product] = []
    for cat in categories:
        names = _SAMPLE_PRODUCTS.get(cat, [f"{cat} Ürünü {i}" for i in range(1, 5)])
        for name in names:
            base_price = round(random.uniform(500, 25000), 2)
            is_fake = random.random() < 0.4  # %40 ihtimalle sahte indirim örüntüsü
            history = _generate_price_history(base_price, history_days, fake_discount=is_fake)
            original_price = round(max(h["price"] for h in history[:-3]) * random.uniform(1.0, 1.05), 2)
            rating = round(random.uniform(3.2, 5.0), 1)

            products.append(Product(
                name=name,
                category=cat,
                url=f"https://ornek-magaza.com/urun/{name.replace(' ', '-').lower()}",
                image_url=f"https://placehold.co/300x300?text={name.replace(' ', '+')}",
                rating=rating,
                current_price=base_price,
                original_price=original_price,
                price_history=history,
            ))
    return products


# ---------------------------------------------------------------------------
# GERÇEK KAZIMA ŞABLONU (opsiyonel, isteğe bağlı geliştirme için)
# ---------------------------------------------------------------------------

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}


def _scrape_site_template(search_url: str) -> List[Product]:
    """Gerçek bir siteden ürün kazımak için ŞABLON fonksiyon.

    Kullanmak için:
    1) search_url'i kazımaya izin veren / kendi kontrolündeki siteye göre ayarla.
    2) Aşağıdaki CSS seçicilerini (soup.select(...)) o sitenin HTML yapısına göre değiştir.
    3) real_scrape() içinden bu fonksiyonu çağır.

    NOT: Fiyat geçmişi genelde tek bir sayfa isteğinden alınamaz; bunun için
    kendi veritabanında (örn. bir SQLite/CSV dosyasında) her taramada
    o günün fiyatını biriktirip zamanla geçmiş oluşturman gerekir.
    """
    products = []
    try:
        resp = requests.get(search_url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # --- ÖRNEK seçiciler; gerçek siteye göre değiştirilmeli ---
        cards = soup.select("div.product-card")
        for card in cards:
            name_el = card.select_one(".product-name")
            price_el = card.select_one(".price-current")
            old_price_el = card.select_one(".price-old")
            rating_el = card.select_one(".rating-value")
            link_el = card.select_one("a")
            img_el = card.select_one("img")

            if not (name_el and price_el):
                continue

            products.append(Product(
                name=name_el.get_text(strip=True),
                category="Bilinmiyor",
                url=link_el["href"] if link_el else "",
                image_url=img_el["src"] if img_el else "",
                rating=float(rating_el.get_text(strip=True)) if rating_el else 0.0,
                current_price=float(price_el.get_text(strip=True).replace(".", "").replace(",", ".").replace("TL", "").strip()),
                original_price=float(old_price_el.get_text(strip=True).replace(".", "").replace(",", ".").replace("TL", "").strip()) if old_price_el else 0.0,
                price_history=[],  # gerçek modda ayrı bir kalıcı depoda tutulmalı
            ))
    except Exception as e:
        print(f"[scraper] Kazıma hatası: {e}")

    return products


def real_scrape(categories: List[str]) -> List[Product]:
    """Eski/genel şablon giriş noktası (artık kullanılmıyor).
    Gerçek çoklu site kazıma için real_scrape_multi_site() fonksiyonunu kullan."""
    return []


def real_scrape_multi_site(categories: List[str], sites: List[str] | None = None):
    """Amazon, Trendyol, Hepsiburada, N11, Teknosa, MediaMarkt üzerinde
    GERÇEK arama yapar (real_scrapers.py) ve sonuçları, disk üzerinde
    biriken gerçek fiyat geçmişiyle (price_history_store.py) birleştirerek
    Product nesnelerine dönüştürür.

    Döndürür: (products, diagnostics) — diagnostics her site/kategori için
    HTTP durumu ve bulunan kart sayısını içerir (bkz. real_scrapers.scrape_all_sites).

    NOT: İlk birkaç günde fiyat geçmişi yetersiz olacağından
    price_analyzer bu ürünleri "yetersiz geçmiş" diyerek eleyecektir -
    bu beklenen ve doğru bir davranıştır (sahte indirim riskine karşı
    temkinli yaklaşım). Sistem birkaç gün/hafta çalıştıkça gerçek
    fırsatlar görünmeye başlar.
    """
    import real_scrapers
    import price_history_store

    raw_items, diagnostics = real_scrapers.scrape_all_sites(categories, sites=sites)

    # Bugünün fiyatlarını kalıcı depoya kaydet (geçmiş biriksin diye)
    price_history_store.record_prices(raw_items)

    products: List[Product] = []
    for item in raw_items:
        url = item.get("url", "")
        history = price_history_store.get_history(url)
        original_price = item.get("original_price") or item.get("current_price")

        products.append(Product(
            name=item.get("name", "Bilinmeyen Ürün"),
            category=item.get("category", "Bilinmiyor"),
            url=url,
            image_url=item.get("image_url", ""),
            rating=item.get("rating"),  # None olabilir, price_analyzer bunu ele alır
            current_price=item.get("current_price"),
            original_price=original_price,
            price_history=history,
            source=item.get("source", ""),
        ))

    return products, diagnostics
