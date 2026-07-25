"""
email_sender.py
---------------
Gerçek fırsat ürünlerini şık HTML kartları halinde bir e-postaya dönüştürüp
Gmail SMTP üzerinden gönderir.

GMAIL AYARI (ÖNEMLİ):
Gmail normal şifrenle SMTP girişine izin vermez. "Uygulama Şifresi"
(App Password) oluşturman gerekir:
  1) Google Hesabı -> Güvenlik -> 2 Adımlı Doğrulama'yı aç.
  2) "Uygulama Şifreleri" bölümünden yeni bir şifre oluştur.
  3) Bu 16 haneli şifreyi GMAIL_APP_PASSWORD olarak Streamlit "Secrets"
     kısmına ekle (config.json'a DEĞİL - şifreler asla config.json'a yazılmaz).
"""

from __future__ import annotations
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List
from price_analyzer import Deal


def build_html_email(deals: List[Deal]) -> str:
    cards = ""
    for d in deals:
        p = d.product
        cards += f"""
        <tr>
          <td style="padding:12px;">
            <table width="100%" cellpadding="0" cellspacing="0"
                   style="background:#ffffff;border-radius:14px;overflow:hidden;
                          box-shadow:0 2px 8px rgba(0,0,0,0.08);border:1px solid #eee;">
              <tr>
                <td style="width:110px;padding:14px;vertical-align:top;">
                  <img src="{p.image_url}" width="100" height="100"
                       style="border-radius:10px;object-fit:cover;" alt="{p.name}">
                </td>
                <td style="padding:14px 14px 14px 0;vertical-align:top;">
                  <div style="font-size:15px;font-weight:700;color:#1a1a2e;margin-bottom:4px;">
                    {p.name}
                  </div>
                  <div style="font-size:12px;color:#888;margin-bottom:8px;">
                    {p.category} &nbsp;•&nbsp; ⭐ {p.rating}/5
                  </div>
                  <div style="margin-bottom:6px;">
                    <span style="text-decoration:line-through;color:#aaa;font-size:13px;">
                      {p.original_price:,.2f} TL
                    </span>
                    &nbsp;
                    <span style="background:#e8f9ee;color:#1e9e5a;font-weight:700;
                                  font-size:12px;padding:3px 8px;border-radius:20px;">
                      -%{d.discount_pct:.0f}
                    </span>
                  </div>
                  <div style="font-size:20px;font-weight:800;color:#e63946;margin-bottom:10px;">
                    {p.current_price:,.2f} TL
                  </div>
                  <a href="{p.url}" style="display:inline-block;background:#1a1a2e;color:#fff;
                     text-decoration:none;padding:8px 16px;border-radius:8px;font-size:13px;
                     font-weight:600;">
                    Ürüne Git →
                  </a>
                </td>
              </tr>
            </table>
          </td>
        </tr>
        """

    html = f"""
    <html>
      <body style="margin:0;padding:0;background:#f4f5f7;font-family:Segoe UI,Arial,sans-serif;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f5f7;padding:20px 0;">
          <tr>
            <td align="center">
              <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;">
                <tr>
                  <td style="padding:20px 12px;">
                    <div style="font-size:24px;font-weight:800;color:#1a1a2e;">
                      🔥 İndirim Fırsatı
                    </div>
                    <div style="font-size:13px;color:#666;margin-top:4px;">
                      Bugün senin için {len(deals)} gerçek indirim bulduk. Sahte indirimler elendi ✅
                    </div>
                  </td>
                </tr>
                {cards}
                <tr>
                  <td style="padding:16px 12px;text-align:center;font-size:11px;color:#999;">
                    Bu e-posta "İndirim Fırsatı" takip sistemin tarafından otomatik oluşturulmuştur.
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """
    return html


def send_email(
    to_email: str,
    gmail_user: str,
    gmail_app_password: str,
    subject: str,
    html_content: str,
) -> tuple[bool, str]:
    """Gmail SMTP (SSL, port 465) üzerinden HTML e-posta gönderir.
    Başarılıysa (True, "ok"), hata varsa (False, hata_mesajı) döner."""

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = gmail_user
        msg["To"] = to_email
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
            server.login(gmail_user, gmail_app_password)
            server.sendmail(gmail_user, to_email, msg.as_string())

        return True, "ok"
    except Exception as e:
        return False, str(e)
