"""
real_scrapers.py
-----------------
Amazon.com.tr, Trendyol, Hepsiburada, N11, Teknosa ve MediaMarkt için
GERÇEK arama sonucu kazıma fonksiyonları.

ÖNEMLİ / SORUMLULUK UYARISI:
- Bu siteler bot/otomasyon trafiğini kısıtlayabilir veya IP'ni geçici
  olarak engelleyebilir. Özellikle Amazon çok agresif bot koruması
  kullanır; bu scraper zamanla veya sık kullanımda çalışmayı durdurabilir.
- CSS seçiciler, sitelerin GENEL/TİPİK HTML yapısına göre en iyi tahminle
  yazılmıştır. Siteler sık HTML güncellediği için, bir site 0 sonuç
  döndürmeye başlarsa seçicilerin güncellenmesi gerekir (bkz. dosya sonu:
  "Seçiciler bozulursa ne yapmalı?").
- Bu modül CAPTCHA çözme, proxy rotasyonu veya IP engelini aşma gibi
  agresif bot-koruması atlatma teknikleri İÇERMEZ. Sadece normal bir
  tarayıcı gibi tek istek atar; engellenirse boş sonuç döner, hatayla
  çökmez.
- Kullanmadan önce her sitenin robots.txt ve kullanım şartlarını kontrol
  etmen ve sorumluluğu almanı öneririm.
"""

from __future__ import annotations
import re
import time
import random
from typing import List, Dict
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8",
}

# Kategori isimlerini her sitedeki arama terimine çeviriyoruz
CATEGORY_QUERY_MAP = {
    "Tablet": "tablet",
    "Telefon": "telefon",
    "Laptop": "laptop",
    "Kamera": "fotoğraf makinesi",
    "Video Ekipmanları": "kamera aksesuar",
    "Ev Ürünleri": "küçük ev aleti",
    "Kulaklık": "kulaklık",
    "Akıllı Saat": "akıllı saat",
}


def _clean_price(text: str) -> float | None:
    """'12.345,67 TL' -> 12345.67 gibi metinleri sayıya çevirir."""
    if not text:
        return None
    text = text.strip().replace("TL", "").replace("₺", "").strip()
    text = text.replace(".", "").replace(",", ".")
    match = re.search(r"[\d.]+", text)
    if not match:
        return None
    try:
        return float(match.group())
    except ValueError:
        return None


def _safe_get(url: str, timeout: int = 12):
    """İsteği atar. Başarılıysa (response, durum_bilgisi) döner;
    durum_bilgisi her zaman doldurulur (teşhis/debug amaçlı)."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        info = {"status_code": resp.status_code, "html_len": len(resp.text)}
        if resp.status_code != 200:
            print(f"[real_scrapers] {url} -> HTTP {resp.status_code}")
            return None, info
        return resp, info
    except Exception as e:
        print(f"[real_scrapers] İstek hatası ({url}): {e}")
        return None, {"status_code": None, "html_len": 0, "error": str(e)}


# ---------------------------------------------------------------------------
# TRENDYOL
# ---------------------------------------------------------------------------
def scrape_trendyol(query: str, category: str, max_items: int = 8) -> List[Dict]:
    url = f"https://www.trendyol.com/sr?q={query.replace(' ', '+')}"
    resp, diag = _safe_get(url)
    if not resp:
        return [], diag
    soup = BeautifulSoup(resp.text, "html.parser")
    items = []
    cards = soup.select("div.p-card-wrppr")[:max_items]
    diag['cards_found'] = len(cards)
    for c in cards:
        try:
            name_el = c.select_one("span.prdct-desc-cntnr-name") or c.select_one("span.prdct-desc-cntnr-ttl")
            price_el = c.select_one("div.prc-box-dscntd") or c.select_one("div.prc-box-sllng")
            old_price_el = c.select_one("div.prc-box-orgnl")
            link_el = c.select_one("a")
            img_el = c.select_one("img")

            if not (name_el and price_el and link_el):
                continue

            items.append({
                "name": name_el.get_text(strip=True),
                "category": category,
                "url": "https://www.trendyol.com" + link_el.get("href", ""),
                "image_url": img_el.get("data-src") or img_el.get("src", "") if img_el else "",
                "current_price": _clean_price(price_el.get_text()),
                "original_price": _clean_price(old_price_el.get_text()) if old_price_el else None,
                "rating": None,
                "source": "Trendyol",
            })
        except Exception:
            continue
    return items, diag


# ---------------------------------------------------------------------------
# HEPSIBURADA
# ---------------------------------------------------------------------------
def scrape_hepsiburada(query: str, category: str, max_items: int = 8) -> List[Dict]:
    url = f"https://www.hepsiburada.com/ara?q={query.replace(' ', '+')}"
    resp, diag = _safe_get(url)
    if not resp:
        return [], diag
    soup = BeautifulSoup(resp.text, "html.parser")
    items = []
    cards = soup.select("li[class*='productListContent'], div[class*='product-item']")[:max_items]
    diag['cards_found'] = len(cards)
    for c in cards:
        try:
            name_el = c.select_one("h3") or c.select_one("[data-test-id='product-card-name']")
            price_el = c.select_one("[data-test-id='price-current-price']") or c.select_one("span[class*='price']")
            link_el = c.select_one("a")
            img_el = c.select_one("img")

            if not (name_el and price_el and link_el):
                continue

            href = link_el.get("href", "")
            items.append({
                "name": name_el.get_text(strip=True),
                "category": category,
                "url": href if href.startswith("http") else "https://www.hepsiburada.com" + href,
                "image_url": img_el.get("src", "") if img_el else "",
                "current_price": _clean_price(price_el.get_text()),
                "original_price": None,
                "rating": None,
                "source": "Hepsiburada",
            })
        except Exception:
            continue
    return items, diag


# ---------------------------------------------------------------------------
# N11
# ---------------------------------------------------------------------------
def scrape_n11(query: str, category: str, max_items: int = 8) -> List[Dict]:
    url = f"https://www.n11.com/arama?q={query.replace(' ', '+')}"
    resp, diag = _safe_get(url)
    if not resp:
        return [], diag
    soup = BeautifulSoup(resp.text, "html.parser")
    items = []
    cards = soup.select("li.column")[:max_items]
    diag['cards_found'] = len(cards)
    for c in cards:
        try:
            name_el = c.select_one("h3.productName")
            price_el = c.select_one("a.newPrice ins") or c.select_one("span.newPrice")
            old_price_el = c.select_one("a.oldPrice del")
            link_el = c.select_one("a.plink")
            img_el = c.select_one("img")

            if not (name_el and price_el and link_el):
                continue

            items.append({
                "name": name_el.get_text(strip=True),
                "category": category,
                "url": link_el.get("href", ""),
                "image_url": img_el.get("data-original") or img_el.get("src", "") if img_el else "",
                "current_price": _clean_price(price_el.get_text()),
                "original_price": _clean_price(old_price_el.get_text()) if old_price_el else None,
                "rating": None,
                "source": "N11",
            })
        except Exception:
            continue
    return items, diag


# ---------------------------------------------------------------------------
# TEKNOSA
# ---------------------------------------------------------------------------
def scrape_teknosa(query: str, category: str, max_items: int = 8) -> List[Dict]:
    url = f"https://www.teknosa.com/arama/?q={query.replace(' ', '+')}"
    resp, diag = _safe_get(url)
    if not resp:
        return [], diag
    soup = BeautifulSoup(resp.text, "html.parser")
    items = []
    cards = soup.select("div.o-campaign-item, div[class*='product-card']")[:max_items]
    diag['cards_found'] = len(cards)
    for c in cards:
        try:
            name_el = c.select_one("[class*='product-title'], h3, h2")
            price_el = c.select_one("[class*='current-price'], [class*='sale-price']")
            old_price_el = c.select_one("[class*='old-price'], del")
            link_el = c.select_one("a")
            img_el = c.select_one("img")

            if not (name_el and price_el and link_el):
                continue

            href = link_el.get("href", "")
            items.append({
                "name": name_el.get_text(strip=True),
                "category": category,
                "url": href if href.startswith("http") else "https://www.teknosa.com" + href,
                "image_url": img_el.get("src", "") if img_el else "",
                "current_price": _clean_price(price_el.get_text()),
                "original_price": _clean_price(old_price_el.get_text()) if old_price_el else None,
                "rating": None,
                "source": "Teknosa",
            })
        except Exception:
            continue
    return items, diag


# ---------------------------------------------------------------------------
# MEDIAMARKT
# ---------------------------------------------------------------------------
def scrape_mediamarkt(query: str, category: str, max_items: int = 8) -> List[Dict]:
    url = f"https://www.mediamarkt.com.tr/tr/search.html?query={query.replace(' ', '+')}"
    resp, diag = _safe_get(url)
    if not resp:
        return [], diag
    soup = BeautifulSoup(resp.text, "html.parser")
    items = []
    cards = soup.select("div[data-test='mms-product-card'], div[class*='product-card']")[:max_items]
    diag['cards_found'] = len(cards)
    for c in cards:
        try:
            name_el = c.select_one("[class*='product-title'], h2, h3")
            price_el = c.select_one("[class*='price'] span") or c.select_one("[data-test='mms-price']")
            link_el = c.select_one("a")
            img_el = c.select_one("img")

            if not (name_el and price_el and link_el):
                continue

            href = link_el.get("href", "")
            items.append({
                "name": name_el.get_text(strip=True),
                "category": category,
                "url": href if href.startswith("http") else "https://www.mediamarkt.com.tr" + href,
                "image_url": img_el.get("src", "") if img_el else "",
                "current_price": _clean_price(price_el.get_text()),
                "original_price": None,
                "rating": None,
                "source": "MediaMarkt",
            })
        except Exception:
            continue
    return items, diag


# ---------------------------------------------------------------------------
# AMAZON.COM.TR (bot koruması güçlü - engellenme ihtimali yüksek)
# ---------------------------------------------------------------------------
def scrape_amazon(query: str, category: str, max_items: int = 8) -> List[Dict]:
    url = f"https://www.amazon.com.tr/s?k={query.replace(' ', '+')}"
    resp, diag = _safe_get(url)
    if not resp:
        return [], diag

    # Amazon çoğu zaman bot trafiğine CAPTCHA sayfası döner; bunu tespit edip
    # sessizce boş liste döndürüyoruz (hataya düşmemek için).
    if "captcha" in resp.text.lower() or "robot" in resp.text.lower()[:2000]:
        print("[real_scrapers] Amazon muhtemelen bot koruması gösterdi, atlanıyor.")
        diag["blocked"] = True
        return [], diag

    soup = BeautifulSoup(resp.text, "html.parser")
    items = []
    cards = soup.select("div[data-component-type='s-search-result']")[:max_items]
    diag['cards_found'] = len(cards)
    for c in cards:
        try:
            name_el = c.select_one("h2 span")
            price_whole = c.select_one("span.a-price-whole")
            price_frac = c.select_one("span.a-price-fraction")
            old_price_el = c.select_one("span.a-price.a-text-price span.a-offscreen")
            link_el = c.select_one("h2 a")
            img_el = c.select_one("img.s-image")

            if not (name_el and price_whole and link_el):
                continue

            price_text = price_whole.get_text(strip=True)
            if price_frac:
                price_text += "." + price_frac.get_text(strip=True)

            href = link_el.get("href", "")
            items.append({
                "name": name_el.get_text(strip=True),
                "category": category,
                "url": href if href.startswith("http") else "https://www.amazon.com.tr" + href,
                "image_url": img_el.get("src", "") if img_el else "",
                "current_price": _clean_price(price_text),
                "original_price": _clean_price(old_price_el.get_text()) if old_price_el else None,
                "rating": None,
                "source": "Amazon",
            })
        except Exception:
            continue
    return items, diag


SITE_SCRAPERS = {
    "Trendyol": scrape_trendyol,
    "Hepsiburada": scrape_hepsiburada,
    "N11": scrape_n11,
    "Teknosa": scrape_teknosa,
    "MediaMarkt": scrape_mediamarkt,
    "Amazon": scrape_amazon,
}


def scrape_all_sites(categories: List[str], sites: List[str] | None = None, delay_sec: float = 1.5):
    """Seçilen kategoriler için, seçilen tüm sitelerde arama yapar.
    Siteler arasında (ve istekler arasında) küçük bir bekleme koyarak
    sunucuları/anti-bot sistemlerini gereksiz yormamaya çalışır.

    Döndürür: (all_items, diagnostics)
    diagnostics: [{"site": ..., "category": ..., "status_code": ..., "html_len": ...,
                   "cards_found": ..., "blocked": bool (varsa)}, ...]
    Bu bilgi, bir site 0 sonuç döndürdüğünde bunun "engellenme" mi yoksa
    "seçiciler HTML ile uyuşmuyor" mu olduğunu ayırt etmeye yarar:
    - status_code 200 ama cards_found 0 -> seçiciler güncel değil
    - status_code 403/429/None -> muhtemelen engellenmiş
    """

    sites = sites or list(SITE_SCRAPERS.keys())
    all_items: List[Dict] = []
    diagnostics: List[Dict] = []

    for category in categories:
        query = CATEGORY_QUERY_MAP.get(category, category)
        for site_name in sites:
            scraper_fn = SITE_SCRAPERS.get(site_name)
            if not scraper_fn:
                continue
            try:
                results, diag = scraper_fn(query, category)
                diag = dict(diag or {})
                diag["site"] = site_name
                diag["category"] = category
                diag["items_found"] = len(results)
                diagnostics.append(diag)
                print(f"[real_scrapers] {site_name} / {category}: {len(results)} ürün bulundu | {diag}")
                all_items.extend(results)
            except Exception as e:
                diagnostics.append({"site": site_name, "category": category, "error": str(e)})
                print(f"[real_scrapers] {site_name} kazıma hatası: {e}")
            time.sleep(delay_sec + random.uniform(0, 0.5))

    # Fiyatı okunamayan ürünleri ele
    all_items = [i for i in all_items if i.get("current_price")]
    return all_items, diagnostics


"""
Seçiciler bozulursa ne yapmalı?
--------------------------------
Bir site sürekli 0 ürün döndürmeye başlarsa:
1) Telefonunda Chrome ile o sitede aynı aramayı yap.
2) Bir ürün kartına uzun bas -> "Öğeyi denetle" (Inspect) ile HTML'i aç
   (Chrome mobilde bunun için "masaüstü sitesi" moduna geçmen ve
   chrome://inspect ile bilgisayardan bağlanman gerekebilir; en kolayı
   bilgisayardan bir kez kontrol etmektir).
3) Ürün adı, fiyat ve link'in hangi class/etiket içinde olduğunu bulup
   yukarıdaki ilgili scrape_xxx fonksiyonundaki .select_one(...) satırlarını
   güncelle.
"""
