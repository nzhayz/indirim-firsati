"""
price_analyzer.py
------------------
Ürün listesini alır, fiyat geçmişine bakarak "sahte indirim" örüntüsü
gösteren ürünleri eler ve kullanıcının filtrelerine (min. indirim oranı,
min. puan, analiz süresi, maksimum ürün sayısı) uyan GERÇEK fırsatları
döndürür.

Sahte indirim tespiti mantığı:
- Belirlenen analiz penceresi (örn. son 90 gün) içindeki fiyat geçmişi incelenir.
- Eğer fiyat, "indirim" başlamadan hemen önceki birkaç gün içinde önceki
  seviyesine göre belirgin şekilde (>%10) yükseltilmiş ve hemen ardından
  düşürülmüşse -> SAHTE İNDİRİM kabul edilir ve reddedilir.
- Ürün ancak şu ikisini birden sağlıyorsa GERÇEK İNDİRİM sayılır:
    1) Güncel fiyat, analiz penceresindeki en düşük fiyata eşit (ya da çok yakın).
    2) Güncel fiyat, pencere içindeki "zam öncesi" normal seviyeye göre
       gerçekten daha düşük (suni zam sonrası eski fiyata dönüş değil).
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List
from scraper import Product


@dataclass
class Deal:
    product: Product
    discount_pct: float
    lowest_in_window: float
    is_genuine: bool
    reason: str


def _is_fake_discount(product: Product, window_days: int) -> tuple[bool, str]:
    history = product.price_history[-(window_days + 1):] if product.price_history else []
    if len(history) < 5:
        # Yeterli geçmiş yoksa temkinli davran, gerçek indirim olarak kabul etme.
        return True, "Yetersiz fiyat geçmişi"

    prices = [h["price"] for h in history]
    current = prices[-1]

    # Son 10 günlük periyotta ani bir yükseliş var mı diye kontrol et
    recent_window = prices[-11:-1] if len(prices) >= 11 else prices[:-1]
    if not recent_window:
        return True, "Yetersiz veri"

    pre_hike_baseline = min(recent_window)
    peak_in_recent = max(recent_window)

    hike_ratio = (peak_in_recent - pre_hike_baseline) / pre_hike_baseline if pre_hike_baseline > 0 else 0

    # Eğer son günlerde %10'dan fazla suni zam yapılıp şimdi o zamki fiyata
    # yakın bir seviyeye "indirim" olarak dönülüyorsa -> sahte
    if hike_ratio > 0.10 and current >= pre_hike_baseline * 0.97:
        return True, "Önce zam yapılıp sonra eski fiyata dönülmüş (sahte indirim)"

    return False, "Gerçek indirim"


def analyze_products(
    products: List[Product],
    min_discount_pct: float,
    min_rating: float,
    history_days: int,
    max_results: int,
) -> List[Deal]:
    """Filtrelere uyan ve sahte indirim testinden geçen ürünleri döndürür."""

    deals: List[Deal] = []

    for p in products:
        # Gerçek kazımada bazı sitelerden puan bilgisi çekilemeyebilir (None).
        # Bu durumda puan filtresini uygulamıyoruz (bilinmeyen != düşük puan).
        if p.rating is not None and p.rating < min_rating:
            continue
        if p.discount_pct < min_discount_pct:
            continue

        history_window = p.price_history[-(history_days + 1):] if p.price_history else []
        if not history_window:
            continue

        lowest_in_window = min(h["price"] for h in history_window)

        # Sadece "son N günün en düşük fiyatı" olan ürünler kabul edilir
        if p.current_price > lowest_in_window * 1.01:
            continue

        is_fake, reason = _is_fake_discount(p, history_days)
        if is_fake:
            continue

        deals.append(Deal(
            product=p,
            discount_pct=p.discount_pct,
            lowest_in_window=lowest_in_window,
            is_genuine=True,
            reason=reason,
        ))

    # En yüksek indirim oranına göre sırala
    deals.sort(key=lambda d: d.discount_pct, reverse=True)

    return deals[:max_results]
