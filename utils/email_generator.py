"""
HTML formatında e-posta içerikleri oluşturmak için yardımcı fonksiyonlar.

Bu modül, servis formu verilerini alarak Fiyat Teklifi ve Servis Tamamlandı
bildirimleri için dinamik HTML e-postaları üretir.
"""
import os
import base64
import logging
from datetime import datetime
from decimal import Decimal

def _get_logo_html(logo_path: str) -> str:
    """Verilen yoldan logo resmini base64 formatında HTML'e gömer."""
    if not logo_path or not os.path.exists(logo_path):
        return ""
    try:
        with open(logo_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        mime_type = "image/png" if logo_path.lower().endswith(".png") else "image/jpeg"
        return f'<img src="data:{mime_type};base64,{encoded_string}" alt="Firma Logosu" style="max-width: 200px; height: auto;">'
    except Exception as e:
        print(f"HTML için logo oluşturulurken hata: {e}")
        return ""

def _get_base_html_style() -> str:
    """E-postalar için temel CSS stilini döndürür."""
    return """
    <style>
        @page {
            size: A4;
            margin: 1cm;
        }
        body { 
            font-family: Arial, sans-serif; 
            color: #333; 
            margin: 0; 
            padding: 0; 
            background-color: #fff;
            width: 100%;
        }
        .container { 
            width: 100%; 
            max-width: none;
            margin: 0; 
            padding: 0; 
            border: none; 
            background-color: #fff; 
        }
        .header, .footer { text-align: center; padding-bottom: 20px; }
        .content-table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        .content-table th, .content-table td { padding: 10px 14px; border: 1px solid #ddd; text-align: left; }
        .content-table th { background-color: #fff; font-weight: bold; }
        .total-row td { border-top: 2px solid black; font-weight: bold; font-size: 1.1em; }
        .note { text-align: right; font-style: italic; font-size: 0.9em; margin-top: 15px; color: #555; }
        h1 { color: #2c3e50; text-align: right; }
        h3 { color: #2c3e50; text-align: left; }
        hr { border: none; border-top: 1px solid #eee; margin: 20px 0; }
        .header-table { width: 100%; border: none; margin-bottom: 20px; }
        .header-table td { border: none; padding: 0; }
        .logo-cell { text-align: left; vertical-align: middle; }
        .title-cell { text-align: right; vertical-align: top; }
    </style>
    """

def _get_email_html_style() -> str:
    """E-posta için güvenli CSS stilini döndürür (email client compatible)."""
    return """
    <style>
        body {
            font-family: Arial, sans-serif;
            color: #333;
            margin: 0;
            padding: 10px;
            background-color: #ffffff;
            line-height: 1.4;
            font-size: 14px;
        }
        .container {
            max-width: 100%;
            width: 100%;
            margin: 0 auto;
            background-color: #ffffff;
            padding: 10px;
            box-sizing: border-box;
        }
        .header-table {
            width: 100%;
            border: none;
            margin-bottom: 15px;
            border-bottom: 3px solid #333;
            padding-bottom: 10px;
        }
        .header-table td {
            border: none;
            padding: 5px;
        }
        .logo-cell {
            text-align: left;
            vertical-align: middle;
            width: 40%;
        }
        .logo-cell img {
            max-width: 150px;
            height: auto;
        }
        .title-cell {
            text-align: right;
            vertical-align: middle;
            width: 60%;
        }
        h1 {
            color: #28a745;
            margin: 0 0 5px 0;
            font-size: 22px;
            font-weight: bold;
            line-height: 1.2;
        }
        h3 {
            color: #2c3e50;
            margin-top: 20px;
            margin-bottom: 8px;
            font-size: 16px;
        }
        h4 {
            color: #007bff;
            margin-top: 15px;
            margin-bottom: 8px;
            font-size: 14px;
        }
        p {
            margin: 8px 0;
            font-size: 14px;
            line-height: 1.4;
        }
        .info-box, .warning-box, .success-box {
            background-color: #e7f3ff;
            border-left: 3px solid #2196F3;
            padding: 10px;
            margin: 15px 0;
            border-radius: 3px;
        }
        .warning-box {
            background-color: #fff3cd;
            border-left-color: #ffc107;
        }
        .success-box {
            background-color: #d4edda;
            border-left-color: #28a745;
        }
        .content-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
            border: 1px solid #ddd;
            font-size: 12px;
        }
        .content-table th,
        .content-table td {
            padding: 8px 4px;
            border: 1px solid #ddd;
            text-align: left;
            word-wrap: break-word;
        }
        .content-table th {
            background-color: #f8f9fa;
            font-weight: bold;
            font-size: 12px;
        }
        .total-row td {
            border-top: 2px solid #000;
            font-weight: bold;
            font-size: 13px;
        }
        .note {
            font-style: italic;
            font-size: 12px;
            color: #666;
            margin-top: 10px;
        }
        hr {
            border: none;
            border-top: 1px solid #eee;
            margin: 20px 0;
        }
        .footer {
            font-size: 12px;
            color: #666;
            margin-top: 20px;
        }
        
        /* Mobile-specific styles */
        @media only screen and (max-width: 600px) {
            body {
                padding: 5px;
                font-size: 13px;
            }
            .container {
                padding: 5px;
            }
            .header-table {
                border-bottom: 2px solid #333;
            }
            .logo-cell {
                width: 100%;
                text-align: center;
                display: block;
                margin-bottom: 10px;
            }
            .logo-cell img {
                max-width: 120px;
            }
            .title-cell {
                width: 100%;
                text-align: center;
                display: block;
            }
            h1 {
                font-size: 18px;
            }
            h3 {
                font-size: 15px;
            }
            h4 {
                font-size: 13px;
            }
            .content-table {
                font-size: 10px;
            }
            .content-table th,
            .content-table td {
                padding: 4px 2px;
            }
            .info-box, .warning-box, .success-box {
                padding: 8px;
                margin: 10px 0;
            }
        }
        
        /* Tablet-specific styles */
        @media only screen and (min-width: 601px) and (max-width: 768px) {
            .logo-cell img {
                max-width: 130px;
            }
            h1 {
                font-size: 20px;
            }
        }
    </style>
    """

def generate_quote_html(data: dict) -> str:
    """Fiyat teklifi için HTML e-posta içeriği oluşturur."""
    main_info = data.get('main_info', {})
    
    # Teklif kalemlerini oluştur
    items_html = ""
    grand_total = Decimal('0.00')
    for item in data.get('quote_items', []):
        desc = item.get('description', 'N/A')
        qty = int(item.get('quantity', 0))
        price = Decimal(item.get('unit_price', 0))
        currency = item.get('currency', 'TL')
        total_tl = Decimal(item.get('total_tl', 0))
        grand_total += total_tl
        items_html += f"<tr><td style='padding:6px;border:1px solid #ddd'>{desc}</td><td style='padding:6px;border:1px solid #ddd;text-align:center'>{qty}</td><td style='padding:6px;border:1px solid #ddd;text-align:right'>{price:.2f} {currency}</td><td style='padding:6px;border:1px solid #ddd;text-align:right'>{total_tl:.2f} TL</td></tr>"
    
    # Kompakt HTML
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family:Arial,sans-serif;color:#333;padding:15px;line-height:1.5">
<h2 style="color:#003366;margin:0 0 5px 0">Fiyat Teklifi</h2>
<p style="margin:0;font-size:13px"><strong>Servis No:</strong> {main_info.get('id','N/A')}<br><strong>Tarih:</strong> {datetime.now().strftime('%d.%m.%Y')}</p>
<hr style="border:none;border-top:2px solid #333;margin:10px 0">
<h3 style="color:#2c3e50;font-size:15px;margin:15px 0 8px 0">Müşteri Bilgileri</h3>
<p style="margin:5px 0;font-size:13px">
<strong>İsim:</strong> {main_info.get('customer_name','N/A')} | <strong>Telefon:</strong> {main_info.get('customer_phone','N/A')}<br>
<strong>Adres:</strong> {main_info.get('customer_address','N/A')}<br>
<strong>Cihaz:</strong> {main_info.get('device_model','N/A')} (Seri No: {main_info.get('device_serial','N/A')})
</p>
<h3 style="color:#2c3e50;font-size:15px;margin:15px 0 8px 0">Teklif Kalemleri</h3>
<table style="width:100%;border-collapse:collapse;font-size:12px">
<tr style="background:#f8f9fa">
<th style="padding:6px;border:1px solid #ddd;text-align:left">Açıklama</th>
<th style="padding:6px;border:1px solid #ddd;text-align:center">Adet</th>
<th style="padding:6px;border:1px solid #ddd;text-align:right">Birim Fiyat</th>
<th style="padding:6px;border:1px solid #ddd;text-align:right">Toplam (TL)</th>
</tr>
{items_html}
<tr style="font-weight:bold;border-top:2px solid #000">
<td colspan="3" style="padding:6px;border:1px solid #ddd;text-align:right">GENEL TOPLAM:</td>
<td style="padding:6px;border:1px solid #ddd;text-align:right">{grand_total:.2f} TL</td>
</tr>
</table>
<p style="font-size:11px;color:#666;margin:8px 0;font-style:italic">* Fiyatlara KDV dahil değildir.</p>
<hr style="border:none;border-top:1px solid #ddd;margin:15px 0">
<p style="margin:8px 0;font-size:13px"><strong>Müşteri Onayı Bekleniyor</strong></p>
<p style="margin:5px 0;font-size:13px">Değişmesi gereken parça/parçaların fiyatı sunulmuştur. Onay vermeniz durumunda onarım işlemi başlatılacaktır.</p>
<p style="margin:5px 0;font-size:13px">Onayınızı telefon, e-posta veya bizzat gelerek verebilirsiniz.</p>
</body>
</html>"""

def generate_repaired_email_html(data: dict) -> str:
    """'Onarıldı' durumu için detaylı servis tamamlama raporu e-postası oluşturur."""
    main_info = data.get('main_info', {})
    company_info = data.get('company_info', {})
    
    # Parça bilgilerini hazırla
    quote_items = data.get('quote_items', [])
    items_html = ""
    grand_total = Decimal('0.00')
    for item in quote_items:
        desc = item.get('description', 'N/A')
        qty = Decimal(item.get('quantity', 1))
        price = Decimal(item.get('unit_price', 0))
        currency = item.get('currency', 'TL')
        total_tl = Decimal(item.get('total_tl', 0))
        grand_total += total_tl
        items_html += f"<tr><td style='padding:6px;border:1px solid #ddd'>{desc}</td><td style='padding:6px;border:1px solid #ddd;text-align:center'>{qty}</td><td style='padding:6px;border:1px solid #ddd;text-align:right'>{price:.2f} {currency}</td><td style='padding:6px;border:1px solid #ddd;text-align:right'>{total_tl:.2f} TL</td></tr>"
    
    # Kompakt HTML
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family:Arial,sans-serif;color:#333;padding:15px;line-height:1.5">
<h2 style="color:#003366;margin:0 0 5px 0">SERVİS TAMAMLAMA RAPORU</h2>
<hr style="border:none;border-top:2px solid #333;margin:10px 0">
<h3 style="color:#2c3e50;font-size:15px;margin:15px 0 8px 0">Firma:</h3>
<p style="margin:5px 0;font-size:13px">
<strong>{company_info.get('company_name','N/A')}</strong><br>
<strong>Adres:</strong> {company_info.get('company_address','N/A')}<br>
<strong>Telefon:</strong> {company_info.get('company_phone','N/A')}<br>
<strong>Email:</strong> {company_info.get('company_email','N/A')}
</p>
<h3 style="color:#2c3e50;font-size:15px;margin:15px 0 8px 0">Müşteri:</h3>
<p style="margin:5px 0;font-size:13px">
<strong>{main_info.get('customer_name','N/A')}</strong><br>
<strong>Telefon:</strong> {main_info.get('customer_phone','N/A')}<br>
<strong>Adres:</strong> {main_info.get('customer_address','N/A')}<br>
<strong>Vergi No:</strong> {main_info.get('customer_tax_id','') or '-'}
</p>
<h3 style="color:#2c3e50;font-size:15px;margin:15px 0 8px 0">SERVİS BİLGİLERİ</h3>
<p style="margin:5px 0;font-size:13px">
<strong>Servis No:</strong> {main_info.get('id','N/A')} | <strong>Servis Tarihi:</strong> {main_info.get('created_date','N/A')}<br>
<strong>Cihaz Model:</strong> {main_info.get('device_model','N/A')} | <strong>Seri No:</strong> {main_info.get('device_serial','N/A')}<br>
<strong>Teknisyen:</strong> {main_info.get('technician_name','N/A')} | <strong>Durum:</strong> ONARILDI<br>
<strong>Onarım Tarihi:</strong> {datetime.now().strftime('%d.%m.%Y %H:%M')}<br>
<strong>BW Sayaç:</strong> {main_info.get('bw_counter','N/A')}
</p>
<h3 style="color:#2c3e50;font-size:15px;margin:15px 0 8px 0">BİLDİRİLEN ARIZA</h3>
<p style="margin:5px 0;font-size:13px;background:#f5f5f5;padding:10px;border-left:3px solid #dc3545">
{main_info.get('problem_description','Belirtilmedi').replace(chr(10),'<br>')}
</p>
<h3 style="color:#2c3e50;font-size:15px;margin:15px 0 8px 0">YAPILAN İŞLEMLER</h3>
<p style="margin:5px 0;font-size:13px;background:#f5f5f5;padding:10px;border-left:3px solid #28a745">
{main_info.get('notes','Belirtilmedi').replace(chr(10),'<br>')}
</p>
<h3 style="color:#2c3e50;font-size:15px;margin:15px 0 8px 0">TEKNİSYEN RAPORU</h3>
<p style="margin:5px 0;font-size:13px;background:#f5f5f5;padding:10px;border-left:3px solid #007bff">
{main_info.get('technician_report','Belirtilmedi').replace(chr(10),'<br>')}
</p>
<h3 style="color:#2c3e50;font-size:15px;margin:15px 0 8px 0">KULLANILAN PARÇALAR</h3>
<table style="width:100%;border-collapse:collapse;font-size:12px">
<tr style="background:#f8f9fa">
<th style="padding:6px;border:1px solid #ddd;text-align:left">Parça Adı</th>
<th style="padding:6px;border:1px solid #ddd;text-align:center">Miktar</th>
<th style="padding:6px;border:1px solid #ddd;text-align:right">Birim Fiyat</th>
<th style="padding:6px;border:1px solid #ddd;text-align:right">Toplam</th>
</tr>
{items_html}
<tr style="font-weight:bold">
<td colspan="3" style="padding:6px;border:1px solid #ddd;text-align:right">Toplam tutar:</td>
<td style="padding:6px;border:1px solid #ddd;text-align:right">{grand_total:,.2f} TL</td>
</tr>
</table>
<p style="font-size:11px;color:#666;margin:8px 0;font-style:italic">* Fiyatlara KDV dahil değildir.</p>
<hr style="border:none;border-top:1px solid #ddd;margin:15px 0">
<p style="margin:8px 0;font-size:13px">Detaylı rapor için ekteki PDF dosyasını inceleyiniz.</p>
<p style="margin:8px 0;font-size:13px">İyi günler dileriz,<br><strong>{company_info.get('company_name','')}</strong></p>
</body>
</html>"""


def generate_ready_for_delivery_email_html(data: dict) -> str:
    """'Teslimat Sürecinde' durumu için e-posta içeriği oluşturur."""
    main_info = data.get('main_info', {})
    company_info = data.get('company_info', {})
    
    # Kompakt HTML
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family:Arial,sans-serif;color:#333;padding:15px;line-height:1.5">
<h2 style="color:#28a745;margin:0 0 5px 0">Cihazınız Teslim Edilecek</h2>
<p style="margin:0;font-size:13px"><strong>Servis No:</strong> {main_info.get('id','N/A')}<br><strong>Tarih:</strong> {datetime.now().strftime('%d.%m.%Y')}</p>
<hr style="border:none;border-top:2px solid #333;margin:10px 0">
<h3 style="color:#2c3e50;font-size:15px;margin:15px 0 8px 0">Sayın {main_info.get('customer_name','N/A')},</h3>
<p style="margin:5px 0;font-size:13px"><strong>{main_info.get('device_model','N/A')}</strong> model cihazınız (Seri No: <strong>{main_info.get('device_serial','N/A')}</strong>) teslimat sürecine alınmıştır.</p>
<h3 style="color:#007bff;font-size:15px;margin:15px 0 8px 0">İletişim Bilgileriniz</h3>
<p style="margin:5px 0;font-size:13px">
<strong>Telefon:</strong> {main_info.get('customer_phone','N/A')}<br>
<strong>Adres:</strong> {main_info.get('customer_address','N/A')}
</p>
<div style="background:#d4edda;border-left:3px solid #28a745;padding:10px;margin:15px 0">
<h4 style="color:#155724;margin:0 0 8px 0;font-size:14px">✅ Teslimat Bilgisi</h4>
<p style="margin:5px 0;font-size:13px"><strong>Cihazınız en kısa zamanda size teslim edilecektir.</strong></p>
<p style="margin:5px 0;font-size:13px">Teslimat için sizinle iletişime geçilecek veya cihazınızı firmamızdan teslim alabilirsiniz.</p>
</div>
<hr style="border:none;border-top:1px solid #ddd;margin:15px 0">
<p style="margin:8px 0;font-size:13px">Herhangi bir sorunuz olması durumunda bizimle iletişime geçebilirsiniz.</p>
<p style="margin:8px 0;font-size:13px">İyi günler dileriz,<br><strong>{company_info.get('company_name','')}</strong><br>
<strong>Telefon:</strong> {company_info.get('company_phone','')}<br>
<strong>Email:</strong> {company_info.get('company_email','')}</p>
</body>
</html>"""


# Geriye dönük uyumluluk için eski fonksiyon adını koruyalım
def generate_completion_email_html(data: dict) -> str:
    """Servis tamamlama bildirimi için HTML e-posta içeriği oluşturur.
    Not: Bu fonksiyon artık generate_repaired_email_html'i çağırıyor."""
    return generate_repaired_email_html(data)
