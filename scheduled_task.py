"""
scheduled_task.py
------------------
Streamlit arayüzünü açmana gerek kalmadan, config.json'daki ayarlara göre
taramayı çalıştırıp uygun fırsatları otomatik e-posta ile gönderen script.

Bu dosya GitHub Actions (bkz. .github/workflows/daily_scan.yml) tarafından
her gün belirli bir saatte otomatik tetiklenmek için tasarlanmıştır. Böylece
telefonundan uygulamayı hiç açmasan bile, sistem arka planda kendi kendine
çalışıp sana e-posta gönderebilir.

Ortam değişkenleri (GitHub Actions secrets üzerinden sağlanır):
    GMAIL_USER, GMAIL_APP_PASSWORD

Çalıştırma:
    python scheduled_task.py
"""

import json
import os
import sys

from scraper import simulate_scrape, real_scrape_multi_site
from price_analyzer import analyze_products
from email_sender import build_html_email, send_email

CONFIG_PATH = "config.json"


def main():
    if not os.path.exists(CONFIG_PATH):
        print("config.json bulunamadı. Önce Streamlit arayüzünden ayarları kaydet.")
        sys.exit(1)

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    if not cfg.get("categories"):
        print("config.json içinde hiç kategori seçilmemiş, çıkılıyor.")
        return

    if not cfg.get("email"):
        print("config.json içinde e-posta adresi tanımlı değil, çıkılıyor.")
        return

    gmail_user = os.environ.get("GMAIL_USER", "")
    gmail_pass = os.environ.get("GMAIL_APP_PASSWORD", "")

    if not gmail_user or not gmail_pass:
        print("GMAIL_USER / GMAIL_APP_PASSWORD ortam değişkenleri tanımlı değil, çıkılıyor.")
        sys.exit(1)

    print(f"Taranıyor: {cfg['categories']}")
    if cfg.get("data_source") == "Gerçek Kazıma":
        products = real_scrape_multi_site(cfg["categories"], sites=cfg.get("sites"))
    else:
        products = simulate_scrape(cfg["categories"], history_days=cfg["history_days"])

    deals = analyze_products(
        products,
        min_discount_pct=cfg["min_discount_pct"],
        min_rating=cfg["min_rating"],
        history_days=cfg["history_days"],
        max_results=cfg["max_products"],
    )

    print(f"{len(deals)} gerçek indirim fırsatı bulundu.")

    if not deals:
        print("Uygun fırsat yok, e-posta gönderilmedi.")
        return

    html = build_html_email(deals)
    ok, msg = send_email(
        to_email=cfg["email"],
        gmail_user=gmail_user,
        gmail_app_password=gmail_pass,
        subject=f"🔥 {len(deals)} yeni indirim fırsatı bulundu!",
        html_content=html,
    )

    if ok:
        print("E-posta başarıyla gönderildi.")
    else:
        print(f"E-posta gönderilemedi: {msg}")
        sys.exit(1)


if __name__ == "__main__":
    main()
