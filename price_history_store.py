"""
price_history_store.py
-----------------------
Gerçek kazıma modu, tek bir andaki fiyatı görebilir; geçmişi göremez.
Bu modül, her taramada o günün fiyatını `data/price_history.json` dosyasına
ekleyerek zamanla gerçek bir fiyat geçmişi biriktirir.

ÖNEMLİ: Bu dosyanın kalıcı olması için, GitHub Actions (scheduled_task.py)
her çalıştığında güncellenmiş price_history.json'ı repoya GERİ COMMIT'lemesi
gerekir (bkz. .github/workflows/daily_scan.yml -> "Değişiklikleri commit'le"
adımı). Streamlit Cloud üzerinden yapılan manuel "Taramayı Başlat" işlemleri
bu dosyayı repoya geri yazamaz (Streamlit Cloud'un git yazma yetkisi yoktur),
bu yüzden düzenli/güvenilir geçmiş birikimi GitHub Actions üzerinden olur.
"""

from __future__ import annotations
import json
import os
import datetime as dt
from typing import List, Dict

STORE_PATH = "data/price_history.json"
MAX_HISTORY_DAYS = 120  # bellekte tutulan üst sınır (sonra otomatik budanır)


def _load_store() -> dict:
    if not os.path.exists(STORE_PATH):
        return {}
    try:
        with open(STORE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_store(store: dict):
    os.makedirs(os.path.dirname(STORE_PATH), exist_ok=True)
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)


def record_prices(items: List[Dict]) -> None:
    """Bugünün fiyatlarını her ürün için (url anahtarıyla) depoya ekler."""
    store = _load_store()
    today = str(dt.date.today())

    for item in items:
        url = item.get("url")
        price = item.get("current_price")
        if not url or price is None:
            continue

        history = store.get(url, [])
        # Aynı gün için tekrar kayıt varsa güncelle, yoksa ekle
        history = [h for h in history if h["date"] != today]
        history.append({"date": today, "price": price})

        # Çok eski kayıtları buda
        cutoff = dt.date.today() - dt.timedelta(days=MAX_HISTORY_DAYS)
        history = [h for h in history if dt.date.fromisoformat(h["date"]) >= cutoff]

        store[url] = sorted(history, key=lambda h: h["date"])

    _save_store(store)


def get_history(url: str) -> List[Dict]:
    store = _load_store()
    return store.get(url, [])


def days_tracked(url: str) -> int:
    return len(get_history(url))
