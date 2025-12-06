"""
PDF oluşturma işlemleri için yardımcı fonksiyonlar.

Bu modül, ReportLab kütüphanesini kullanarak çeşitli PDF belgeleri (faturalar,
teklif formları, raporlar) oluşturur. Özel fontları (DejaVu) kaydederek
Türkçe karakter desteği sağlar ve modern, tutarlı bir tasarım sunar.
"""
import os
import logging
import uuid
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from datetime import datetime
from typing import List, Dict, Any, Tuple

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image, Flowable
)
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm, inch
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Import currency converter
from .currency_converter import get_exchange_rates

# Logging yapılandırması
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- FONT YÖNETİMİ ---

def register_fonts():
    """
    Proje klasöründeki 'resources/fonts' klasöründeki DejaVu fontlarını ReportLab'e kaydeder.
    Bu fonksiyon, PDF'lerde Türkçe karakterlerin doğru görüntülenmesi için gereklidir.
    """
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        font_folder = os.path.join(base_dir, 'resources', 'fonts')
        
        fonts_to_register = {
            'DejaVuSans': 'DejaVuSans.ttf',
            'DejaVuSans-Bold': 'DejaVuSans-Bold.ttf',
            'DejaVuSans-Oblique': 'DejaVuSans-Oblique.ttf',
            'DejaVuSans-BoldOblique': 'DejaVuSans-BoldOblique.ttf',
        }

        for name, filename in fonts_to_register.items():
            path = os.path.join(font_folder, filename)
            if os.path.exists(path):
                if name not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont(name, path))
                    logging.info(f"'{name}' fontu başarıyla kaydedildi.")
            else:
                logging.warning(f"Font dosyası bulunamadı, kaydedilemedi: {path}")
    except Exception as e:
        logging.error(f"Fontları kaydederken beklenmedik bir hata oluştu: {e}", exc_info=True)

# Uygulama başlangıcında fontları kaydet
register_fonts()

def get_font_names() -> Tuple[str, str]:
    """
    Sistemde kayıtlı olan DejaVu font adlarını döndürür.
    Eğer DejaVu fontları bulunamazsa, varsayılan Helvetica fontlarını döndürür.

    Returns:
        Tuple[str, str]: Normal ve kalın font adlarını içeren bir tuple.
    """
    if 'DejaVuSans' in pdfmetrics.getRegisteredFontNames():
        return 'DejaVuSans', 'DejaVuSans-Bold'
    logging.warning("DejaVu fontları bulunamadı. Varsayılan Helvetica fontları kullanılacak.")
    return "Helvetica", "Helvetica-Bold"

# --- STİL VE YARDIMCI ELEMANLAR ---

def convert_to_tl(amount: Decimal, currency: str) -> Decimal:
    """
    Belirtilen para birimindeki tutarı güncel kurlarla TL'ye çevirir.
    
    Args:
        amount (Decimal): Çevrilecek tutar
        currency (str): Para birimi (TL, USD, EUR)
        
    Returns:
        Decimal: TL cinsinden tutar
    """
    if currency == 'TL':
        return amount
    
    try:
        rates = get_exchange_rates()
        if currency in rates:
            tl_amount = amount * rates[currency]
            logging.info(f"{amount} {currency} = {tl_amount} TL (Kur: {rates[currency]})")
            return tl_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:
            logging.warning(f"Desteklenmeyen para birimi: {currency}. TL olarak işleniyor.")
            return amount
    except Exception as e:
        logging.error(f"Döviz çevirimi hatası: {e}. TL olarak işleniyor.")
        return amount

def generate_ettn() -> str:
    """
    eETTN (Elektronik Fatura Takip Numarası) üretir.
    16 haneli unique bir numara döndürür.
    
    Returns:
        str: 16 haneli eETTN
    """
    # UUID4'ün ilk 16 karakterini alıp rakamlarla değiştir
    base_uuid = str(uuid.uuid4()).replace('-', '')[:16]
    # Sadece rakamlardan oluşan 16 haneli numara
    ettn = ''.join([str(ord(c) % 10) for c in base_uuid])
    return ettn

def number_to_words_tr(amount: Decimal) -> str:
    """
    Türkçe para miktarını yazıya çevirir.
    
    Args:
        amount (Decimal): TL cinsinden tutar
        
    Returns:
        str: Yazıyla ifade edilen tutar
    """
    ones = ["", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"]
    tens = ["", "", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan"]
    teens = ["on", "on bir", "on iki", "on üç", "on dört", "on beş", "on altı", "on yedi", "on sekiz", "on dokuz"]
    hundreds = ["", "yüz", "iki yüz", "üç yüz", "dört yüz", "beş yüz", "altı yüz", "yedi yüz", "sekiz yüz", "dokuz yüz"]
    
    def convert_hundreds(num):
        result = ""
        if num >= 100:
            if num // 100 == 1:
                result += "yüz "
            else:
                result += ones[num // 100] + " yüz "
            num %= 100
        
        if num >= 20:
            result += tens[num // 10] + " "
            num %= 10
        elif num >= 10:
            result += teens[num - 10] + " "
            num = 0
        
        if num > 0:
            result += ones[num] + " "
        
        return result.strip()
    
    def convert_thousands(num):
        if num == 0:
            return ""
        elif num == 1:
            return "bin"
        elif num < 1000:
            return convert_hundreds(num) + " bin"
        else:
            thousands = num // 1000
            remainder = num % 1000
            result = ""
            if thousands == 1:
                result += "bir milyon "
            else:
                result += convert_hundreds(thousands) + " milyon "
            if remainder > 0:
                result += convert_hundreds(remainder) + " bin"
            return result.strip()
    
    # Ana dönüşüm
    integer_part = int(amount)
    decimal_part = int((amount % 1) * 100)
    
    if integer_part == 0:
        result = "sıfır"
    elif integer_part < 1000:
        result = convert_hundreds(integer_part)
    elif integer_part < 1000000:
        thousands = integer_part // 1000
        remainder = integer_part % 1000
        if thousands == 1:
            result = "bin"
        else:
            result = convert_hundreds(thousands) + " bin"
        if remainder > 0:
            result += " " + convert_hundreds(remainder)
    else:
        millions = integer_part // 1000000
        remainder = integer_part % 1000000
        if millions == 1:
            result = "bir milyon"
        else:
            result = convert_hundreds(millions) + " milyon"
        
        if remainder >= 1000:
            thousands = remainder // 1000
            remainder = remainder % 1000
            if thousands == 1:
                result += " bin"
            else:
                result += " " + convert_hundreds(thousands) + " bin"
        
        if remainder > 0:
            result += " " + convert_hundreds(remainder)
    
    result += " TL"
    
    if decimal_part > 0:
        result += " " + convert_hundreds(decimal_part) + " kuruş"
    
    return result.strip()

def get_professional_styles() -> Dict[str, ParagraphStyle]:
    """
    Profesyonel fatura tasarımı için standart ParagraphStyle nesnelerini döndürür.
    """
    styles = getSampleStyleSheet()
    font_name, font_name_bold = get_font_names()
    
    styles.add(ParagraphStyle(name='Normal_TR', parent=styles['Normal'], fontName=font_name))
    styles.add(ParagraphStyle(name='Heading4_TR', parent=styles['Heading4'], fontName=font_name_bold))
    styles.add(ParagraphStyle(name='Title_TR', parent=styles['Title'], fontName=font_name_bold))
    
    return {
        "styleN": styles['Normal_TR'],
        "styleB": styles['Heading4_TR'],
        "styleT": styles['Title_TR'],
    }

def _create_document_header(comp_info: Dict[str, Any], cust_info: Dict[str, Any]) -> Table:
    """Fatura için Müşteri ve Firma bilgilerini içeren başlık tablosunu oluşturur."""
    styles = get_professional_styles()
    styleN, styleB = styles["styleN"], styles["styleB"]

    customer_box = [
        Paragraph(f"<b>{cust_info.get('name','Müşteri Adı')}</b>", styleB),
        Paragraph(cust_info.get('address','Adres Bilgisi Yok'), styleN),
        Paragraph(f"Tel: {cust_info.get('phone','Telefon Bilgisi Yok')}", styleN),
        Paragraph(f"VD: {cust_info.get('tax_office','')}", styleN),
        Paragraph(f"VKN: {cust_info.get('tax_id','Vergi Numarası Yok')}", styleN),
    ]
    
    # Firma bilgileri için fallback değerler
    # Company bilgilerini güvenli şekilde al
    company_name = comp_info.get('company_name') or comp_info.get('name') or ''
    company_address = comp_info.get('company_address') or comp_info.get('address') or ''
    company_phone = comp_info.get('company_phone') or comp_info.get('phone') or ''
    company_email = comp_info.get('company_email') or comp_info.get('email') or ''
    company_tax_office = comp_info.get('company_tax_office') or comp_info.get('tax_office') or ''
    company_tax_id = comp_info.get('company_tax_id') or comp_info.get('tax_id') or ''
    
    # Eğer firma adı boşsa varsayılan kullan
    if not company_name:
        company_name = 'Firma Adı Belirtilmemiş'
    if not company_address:
        company_address = 'Adres bilgisi henüz girilmemiş'
    if not company_phone:
        company_phone = 'Telefon bilgisi henüz girilmemiş'
    if not company_email:
        company_email = 'Email bilgisi henüz girilmemiş'
    
    company_box = []
    # Logo ekle
    logo_path = comp_info.get('company_logo_path') or comp_info.get('logo_path', '')
    if logo_path and os.path.exists(logo_path):
        try:
            logo_img = Image(logo_path, width=40*mm, height=18*mm)
            company_box.append(logo_img)
        except Exception:
            pass
    company_box += [
        Paragraph(f"<b>{company_name}</b>", styleB),
        Paragraph(company_address, styleN),
        Paragraph(f"Tel: {company_phone}", styleN),
        Paragraph(f"VD: {company_tax_office}", styleN),
        Paragraph(f"VKN: {company_tax_id}", styleN),
        Paragraph(f"E-Posta: {company_email}", styleN),
    ]
    box_table = Table([[customer_box, company_box]], colWidths=[90*mm, 90*mm])
    box_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#E5E7EB')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F9FAFB')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E7EB')),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    return box_table

def _calculate_currency_totals(items: List[Dict[str, Any]]) -> Dict[str, Decimal]:
    """Para birimi bazında toplamları hesaplar."""
    currency_totals = {}
    
    for item in items:
        qty = Decimal(str(item.get('quantity', 1)))
        price = Decimal(str(item.get('unit_price', 0)))
        item_currency = item.get('currency', 'TL')
        
        # Eğer 'total' alanı verilmişse onu kullan, yoksa hesapla
        if 'total' in item and item['total'] is not None:
            try:
                total_value = item['total']
                if isinstance(total_value, str):
                    import re
                    total_value = re.sub(r'[^0-9.,\-]', '', total_value)
                    total_value = total_value.replace(',', '.')
                total = Decimal(str(total_value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            except (ValueError, TypeError, InvalidOperation):
                total = (qty * price).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:
            total = (qty * price).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Para birimi bazında topla
        if item_currency not in currency_totals:
            currency_totals[item_currency] = Decimal('0.00')
        currency_totals[item_currency] += total
    
    return currency_totals

def _create_currency_totals_table(currency_totals: Dict[str, Decimal], vat_rate: Decimal) -> Table:
    """Para birimi bazında toplamları ve TL karşılıklarını gösteren tablo oluşturur."""
    font_name, font_name_bold = get_font_names()
    table_data = []
    total_tl = Decimal('0.00')
    
    # Her para birimi için satır ekle
    # Normalize and display totals primarily in TL. If there are other currencies, show their TL equivalent.
    for currency, amount in currency_totals.items():
        if currency == 'TL':
            amount_tl = amount
            table_data.append([f"Toplam {currency}:", f"{amount:,.2f} {currency}", ""])
        else:
            amount_tl = convert_to_tl(amount, currency)
            # Döviz kuru al
            rates = get_exchange_rates()
            rate = rates.get(currency, 1)
            # Show the foreign currency total as its TL equivalent to avoid confusion
            table_data.append([f"Toplam {currency} (TL karşılığı):", f"{amount_tl:,.2f} TL", f"(Kur: {rate:.4f})"])
        
        total_tl += amount_tl
    
    # KDV hesapla
    total_vat_amount = (total_tl * (vat_rate / 100)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    grand_total_tl = total_tl + total_vat_amount
    
    # Alt toplam ve KDV satırları
    table_data.append(["", "", ""])  # Boş satır
    table_data.append(["Ara Toplam (TL):", "", f"{total_tl:,.2f} TL"])
    table_data.append([f"KDV (%{vat_rate}):", "", f"{total_vat_amount:,.2f} TL"])
    table_data.append(["Vergiler Dahil Toplam:", "", f"{grand_total_tl:,.2f} TL"])
    
    totals_table = Table(table_data, colWidths=[50*mm, 60*mm, 70*mm])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
        ('FONTNAME', (0,0), (-1,-1), font_name),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        # Kur bilgileri için küçük font boyutu
        ('FONTSIZE', (2,0), (2,-4), 7),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#F3F4F6')),
        ('FONTNAME', (0,-1), (0,-1), font_name_bold),
        ('FONTNAME', (0,-2), (0,-2), font_name_bold),
        # Izgara kaldırıldı - sadece önemli satırlar için çizgi
        ('LINEBELOW', (0,-3), (-1,-3), 0.5, colors.black),  # Ara toplam öncesi çizgi
        ('LINEBELOW', (0,-1), (-1,-1), 1, colors.black),    # Son toplam altı çizgi
    ]))
    
    return totals_table, grand_total_tl

def _create_items_table(items: List[Dict[str, Any]], vat_rate: Decimal, currency: str) -> Tuple[Table, Dict[str, Decimal]]:
    """Ürün/hizmet tablosunu oluşturur ve para birimi bazında toplamları döndürür."""
    styles = get_professional_styles()
    styleN = styles["styleN"]
    font_name, font_name_bold = get_font_names()

    headers = ["#", "Açıklama", "Miktar", "Birim Fiyat", "KDV", "Tutar"]
    table_data = [headers]
    currency_totals = {}

    for i, item in enumerate(items, 1):
        desc = item.get('description', 'Açıklama Yok')
        qty = Decimal(str(item.get('quantity', 1)))
        price = Decimal(str(item.get('unit_price', 0)))
        item_currency = item.get('currency', currency)
        price_tl = Decimal(str(item.get('unit_price_tl', price)))
        total_tl = Decimal(str(item.get('total_tl', qty * price_tl)))
        # Açıklama: sadece orijinal birim fiyat ve TL karşılığı (döviz kuru ile çarpılmış gerçek değer)
        if item_currency != 'TL' and price_tl != price:
            desc = f"{desc} ({price:,.3f} {item_currency} ≈ {price_tl:,.4f} TL)"
        else:
            desc = f"{desc} ({price_tl:,.4f} TL)"
        print(f"DEBUG: PDF item {i}: description='{desc}', quantity={qty}, unit_price={price_tl}, currency=TL")
        # Tabloda gösterilecek değerler: show original currency and TL equivalent when applicable
        if item_currency != 'TL' and price != price_tl:
            display_price = f"{price:,.4f} {item_currency} ≈ {price_tl:,.2f} TL"
        else:
            display_price = f"{price_tl:,.2f} TL"
        display_total = f"{total_tl:,.2f} TL"
        
        qty_display = f"{qty:.0f}" if qty == qty.quantize(Decimal('1')) else f"{qty:.2f}"
        table_data.append([
            str(i),
            Paragraph(f"<font name='DejaVuSans'>{desc}</font>", styleN),
            qty_display,
            display_price,
            f"%{vat_rate}",
            display_total
        ])

    items_table = Table(table_data, colWidths=[12*mm, 70*mm, 18*mm, 30*mm, 18*mm, 27*mm])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F8F9FA')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.black),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('ALIGN', (1,1), (1,-1), 'LEFT'),  # Açıklama sütunu sola hizalı
        ('FONTNAME', (0,0), (-1,0), font_name_bold),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('FONTNAME', (0,1), (-1,-1), font_name),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    
    # Para birimi bazında toplamları hesapla
    currency_totals = _calculate_currency_totals(items)
    return items_table, currency_totals

def _create_combined_items_table(items: List[Dict[str, Any]], vat_rate: Decimal, currency: str) -> Tuple[Table, Dict[str, Decimal]]:
    """Birleşik fatura için fatura referansı ile birlikte kalemlerini içeren tabloyu oluşturur. Para birimi bazında hesaplar."""
    styles = get_professional_styles()
    styleN = styles["styleN"]
    font_name, font_name_bold = get_font_names()

    headers = ["#", "Açıklama", "Miktar", "Birim Fiyat", "KDV", "Tutar", "Fatura Ref."]
    table_data = [headers]
    currency_totals = {}

    for i, item in enumerate(items, 1):
        desc = item.get('description', 'Açıklama Yok')
        qty = Decimal(str(item.get('quantity', 1)))
        price = Decimal(str(item.get('unit_price', 0)))
        item_currency = item.get('currency', currency)
        
        # Eğer 'total' alanı verilmişse onu kullan, yoksa hesapla (orijinal para biriminde)
        if 'total' in item and item['total'] is not None:
            try:
                total_value = item['total']
                if isinstance(total_value, str):
                    import re
                    total_value = re.sub(r'[^0-9.,\-]', '', total_value)
                    total_value = total_value.replace(',', '.')
                total_original = Decimal(str(total_value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            except (ValueError, TypeError, InvalidOperation) as e:
                print(f"DEBUG: Total değeri dönüştürme hatası: {item['total']} - Hata: {e}")
                total_original = (qty * price).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:
            total_original = (qty * price).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Para birimi bazında topla
        if item_currency not in currency_totals:
            currency_totals[item_currency] = Decimal('0.00')
        currency_totals[item_currency] += total_original
        
        invoice_ref = item.get('invoice_ref', 'N/A')
        
        # Tabloda gösterilecek değerler (temiz ve okunabilir)
        display_price = f"{price:,.2f} {item_currency}"
        display_total = f"{total_original:,.2f} {item_currency}"
        
        table_data.append([
            str(i),
            Paragraph(f"<font name='DejaVuSans'>{desc}</font>", styleN),
            f"{qty:,.0f}",  # Miktar tam sayı olarak göster
            display_price,
            f"%{vat_rate}",
            display_total,
            invoice_ref
        ])

    items_table = Table(table_data, colWidths=[12*mm, 45*mm, 15*mm, 25*mm, 15*mm, 25*mm, 27*mm])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F8F9FA')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.black),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('ALIGN', (1,1), (1,-1), 'LEFT'),  # Açıklama sütunu sola hizalı
        ('FONTNAME', (0,0), (-1,0), font_name_bold),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('FONTNAME', (0,1), (-1,-1), font_name),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    
    return items_table, currency_totals

def _create_totals_table(subtotal: Decimal, total_vat: Decimal, currency: str, ettn: str = None) -> Table:
    """Ara toplam, KDV ve genel toplamı gösteren tabloyu oluşturur."""
    grand_total = subtotal + total_vat
    font_name, _ = get_font_names()

    table_data = [
        ["Ara Toplam:", f"{subtotal:,.2f} TL"],
        [f"Hesaplanan KDV (%{total_vat / subtotal * 100 if subtotal else 0:.0f}):", f"{total_vat:,.2f} TL"],
        ["Vergiler Dahil Toplam Tutar:", f"{grand_total:,.2f} TL"],
    ]
    
    totals_table = Table(table_data, colWidths=[120*mm, 60*mm])
    
    totals_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
        ('FONTNAME', (0,0), (-1,-1), font_name),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('BACKGROUND', (0,2), (-1,2), colors.HexColor('#F3F4F6')),
        ('FONTNAME', (0,2), (0,2), get_font_names()[1]), # Bold for grand total label
    ]))
    return totals_table

def _create_ettn_and_words_section_currency(grand_total_tl: Decimal, ettn: str = None) -> List[Flowable]:
    """Para birimi sistemi için eETTN ve yazıyla tutarı gösteren bölümü oluşturur."""
    styles = get_professional_styles()
    styleN, styleB = styles["styleN"], styles["styleB"]
    
    # Yazıyla tutar
    amount_in_words = number_to_words_tr(grand_total_tl)
    
    # eETTN üret (verilmemişse)
    if not ettn:
        ettn = generate_ettn()
    
    elements = []
    elements.append(Paragraph(f"<b>eETTN:</b> {ettn}", styleN))
    elements.append(Spacer(1, 2*mm))
    elements.append(Paragraph(f"<b>Yalnız:</b> {amount_in_words}", styleN))
    
    return elements

def _create_ettn_and_words_section(subtotal: Decimal, total_vat: Decimal, ettn: str = None) -> List[Flowable]:
    """eETTN ve yazıyla tutarı gösteren bölümü oluşturur (sola dayalı)."""
    grand_total = subtotal + total_vat
    styles = get_professional_styles()
    styleN, styleB = styles["styleN"], styles["styleB"]
    
    # Yazıyla tutar
    amount_in_words = number_to_words_tr(grand_total)
    
    # eETTN üret (verilmemişse)
    if not ettn:
        ettn = generate_ettn()
    
    elements = []
    elements.append(Paragraph(f"<b>eETTN:</b> {ettn}", styleN))
    elements.append(Spacer(1, 2*mm))
    elements.append(Paragraph(f"<b>Yalnız:</b> {amount_in_words.upper()}", styleN))
    
    return elements

def _merge_duplicate_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Aynı açıklama ve birim fiyatı olan kalemleri birleştirir.
    Miktar ve fatura referanslarını toplar.
    
    Args:
        items: Birleştireceğimiz kalem listesi
        
    Returns:
        List[Dict]: Birleştirilmiş kalem listesi
    """
    merged_dict = {}
    
    for item in items:
        # Anahtarı oluştur: açıklama + birim fiyat + para birimi
        description = item.get('description', '')
        unit_price = item.get('unit_price', 0)
        currency = item.get('currency', 'TL')
        
        key = (description, unit_price, currency)
        
        if key in merged_dict:
            # Mevcut kalemi güncelle - miktar topla
            merged_dict[key]['quantity'] += item.get('quantity', 1)
            
            # Fatura referanslarını birleştir
            existing_refs = merged_dict[key]['invoice_ref']
            new_ref = item.get('invoice_ref', '')
            if new_ref and new_ref not in existing_refs:
                merged_dict[key]['invoice_ref'] += f", {new_ref}"
                
            # Total varsa onu da topla
            if 'total' in item:
                merged_dict[key]['total'] = merged_dict[key].get('total', 0) + item.get('total', 0)
        else:
            # Yeni kalem ekle
            merged_dict[key] = item.copy()
    
    return list(merged_dict.values())

# --- ANA PDF OLUŞTURMA FONKSİYONLARI ---

def create_professional_invoice_pdf(invoice_data: Dict[str, Any], file_path: str) -> bool:
    """
    Modern ve profesyonel bir fatura PDF'i oluşturur.
    Veri yapısı: {'id', 'invoice_date', 'customer_info', 'company_info', 'items', 'vat_rate', 'currency'}
    """
    try:
        doc = SimpleDocTemplate(file_path, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
        elements = []
        styles = get_professional_styles()
        styleN, styleT = styles["styleN"], styles["styleT"]

        comp_info = invoice_data.get('company_info', {})
        cust_info = invoice_data.get('customer_info', {})
        
        # 1. Müşteri ve Firma Bilgileri
        elements.append(_create_document_header(comp_info, cust_info))
        elements.append(Spacer(1, 8*mm))

        # 2. Fatura Başlığı ve Detayları
        try:
            invoice_date_obj = datetime.strptime(invoice_data.get('invoice_date', ''), '%Y-%m-%d')
            invoice_no = f"{invoice_date_obj.strftime('%d%m%y')}-{invoice_data.get('id')}"
            invoice_date_str = invoice_date_obj.strftime('%d.%m.%Y')
        except (ValueError, TypeError):
            invoice_no = str(invoice_data.get('id', 'N/A'))
            invoice_date_str = invoice_data.get('invoice_date', 'N/A')

        details_table = Table([
            [Paragraph("<b>FATURA</b>", styleT),
             Paragraph(f"Fatura No: {invoice_no}<br/>Tarih: {invoice_date_str}", styleN)]
        ], colWidths=[90*mm, 90*mm])
        details_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('ALIGN', (1,0), (1,0), 'RIGHT')]))
        elements.append(details_table)
        elements.append(Spacer(1, 8*mm))

        # 3. Ürün/Hizmet Tablosu ve Toplamlar
        vat_rate = Decimal(invoice_data.get('vat_rate', '20.0'))
        original_currency = invoice_data.get('currency', 'TL')
        
        # Para birimi bazında toplamlar ile items table
        items_table, currency_totals = _create_items_table(invoice_data.get('items', []), vat_rate, original_currency)
        elements.append(items_table)
        elements.append(Spacer(1, 4*mm))
        
        # 4. Para Birimi Bazında Toplamlar Tablosu
        totals_table, grand_total_tl = _create_currency_totals_table(currency_totals, vat_rate)
        elements.append(totals_table)
        elements.append(Spacer(1, 8*mm))

        # 5. eETTN ve Yazıyla Tutar (sola dayalı)
        ettn = invoice_data.get('ettn', None)  # eETTN varsa kullan
        ettn_elements = _create_ettn_and_words_section_currency(grand_total_tl, ettn)
        for element in ettn_elements:
            elements.append(element)
        elements.append(Spacer(1, 8*mm))

        # 6. Banka Bilgileri (tüm bankalar)
        try:
            from .database import db_manager
            banks = db_manager.fetch_all("SELECT bank_name, account_holder, iban FROM banks ORDER BY is_default DESC, bank_name")
            
            if banks:
                elements.append(Paragraph("<b>Banka Bilgileri</b>", styles['styleB']))
                for bank in banks:
                    bank_name, account_holder, iban = bank
                    bank_text = f"Banka: {bank_name}<br/>Hesap Sahibi: {account_holder}<br/>IBAN: {iban}"
                    elements.append(Paragraph(bank_text, styleN))
                    elements.append(Spacer(1, 2*mm))
                elements.append(Spacer(1, 2*mm))
        except Exception as e:
            # Fallback: Eski tek banka sistemi veya company settings'den bilgiler
            bank_info_parts = [
                f"Banka: {comp_info.get('bank_name') or 'Banka bilgisi henüz girilmemiş'}" if comp_info.get('bank_name') else "Banka: Banka bilgisi henüz girilmemiş",
                f"Hesap Sahibi: {comp_info.get('bank_account_holder') or 'Hesap sahibi henüz girilmemiş'}" if comp_info.get('bank_account_holder') else "Hesap Sahibi: Hesap sahibi henüz girilmemiş",
                f"IBAN: {comp_info.get('bank_iban') or 'IBAN henüz girilmemiş'}" if comp_info.get('bank_iban') else "IBAN: IBAN henüz girilmemiş",
            ]
            bank_info_text = "<br/>".join(bank_info_parts)
            elements.append(Paragraph("<b>Banka Bilgileri</b>", styles['styleB']))
            elements.append(Paragraph(bank_info_text, styleN))
            elements.append(Spacer(1, 4*mm))

        # 6. Alt Bilgiler
        elements.append(Paragraph(f"<font size=8>ETTN: ...</font>", styleN))
        elements.append(Paragraph(f"<b>YALNIZ:</b> ...", styleN))

        doc.build(elements)
        logging.info(f"Profesyonel fatura başarıyla oluşturuldu: {file_path}")
        return True
    except Exception as e:
        logging.error(f"Profesyonel fatura oluşturulurken hata: {e}", exc_info=True)
        return False

def create_merged_invoice_pdf(customer_name: str, invoices_data: List[Dict[str, Any]], file_path: str) -> bool:
    """
    Birden fazla faturayı, her biri ayrı bir sayfada olacak şekilde tek bir PDF dosyasında birleştirir.
    """
    import tempfile
    import shutil
    from PyPDF2 import PdfMerger
    try:
        temp_files = []
        from utils.database import db_manager
        import logging
        for i, invoice in enumerate(invoices_data):
            # Geçici dosya oluştur
            temp_fd, temp_path = tempfile.mkstemp(suffix=f'_fatura_{invoice.get("id")}.pdf')
            os.close(temp_fd)
            temp_files.append(temp_path)
            # Gerekli verileri `invoice`'dan al, eksikse ayarlardan doldur
            company_info = invoice.get('company_info')
            if not company_info:
                company_info = {
                    'name': db_manager.get_setting('company_name', 'Firma Adı'),
                    'address': db_manager.get_setting('company_address', 'Adres Bilgisi Yok'),
                    'phone': db_manager.get_setting('company_phone', 'Telefon Bilgisi Yok'),
                    'tax_office': db_manager.get_setting('company_tax_office', ''),
                    'tax_id': db_manager.get_setting('company_tax_id', ''),
                    'email': db_manager.get_setting('company_email', ''),
                    'bank_name': db_manager.get_setting('company_bank_name', ''),
                    'bank_account_holder': db_manager.get_setting('company_bank_account_holder', ''),
                    'bank_iban': db_manager.get_setting('company_bank_iban', ''),
                    'logo_path': db_manager.get_setting('company_logo_path', ''),
                }
            customer_info = invoice.get('customer_info')
            if not customer_info:
                customer_info = {'name': customer_name}
            invoice_data = {
                'id': invoice.get('id'),
                'invoice_date': invoice.get('invoice_date'),
                'customer_info': customer_info,
                'company_info': company_info,
                'items': invoice.get('items', []),
                'vat_rate': invoice.get('vat_rate', '20.0'),
                'currency': invoice.get('currency', 'TL')
            }
            # Her fatura için tek sayfalık PDF oluştur
            try:
                doc = SimpleDocTemplate(temp_path, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
                elements = []
                styles = get_professional_styles()
                styleN, styleT = styles["styleN"], styles["styleT"]
                comp_info = invoice_data.get('company_info', {})
                cust_info = invoice_data.get('customer_info', {})
                elements.append(_create_document_header(comp_info, cust_info))
                elements.append(Spacer(1, 8*mm))
                try:
                    invoice_date_obj = datetime.strptime(invoice_data.get('invoice_date'), '%Y-%m-%d')
                    invoice_no = f"{invoice_date_obj.strftime('%d%m%y')}-{invoice_data.get('id')}"
                    invoice_date_str = invoice_date_obj.strftime('%d.%m.%Y')
                except (ValueError, TypeError):
                    invoice_no = str(invoice_data.get('id', 'N/A'))
                    invoice_date_str = invoice_data.get('invoice_date', 'N/A')
                details_table = Table([[Paragraph("<b>FATURA</b>", styleT), Paragraph(f"Fatura No: {invoice_no}<br/>Tarih: {invoice_date_str}", styleN)]], colWidths=[90*mm, 90*mm])
                details_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('ALIGN', (1,0), (1,0), 'RIGHT')]))
                elements.append(details_table)
                elements.append(Spacer(1, 8*mm))
                vat_rate = Decimal(invoice_data.get('vat_rate', '20.0'))
                original_currency = invoice_data.get('currency', 'TL')
                items_table, subtotal, total_vat = _create_items_table(invoice_data.get('items', []), vat_rate, original_currency)
                elements.append(items_table)
                elements.append(Spacer(1, 4*mm))
                ettn = invoice_data.get('ettn', None)
                elements.append(_create_totals_table(subtotal, total_vat, 'TL'))
                elements.append(Spacer(1, 8*mm))
                
                # eETTN ve Yazıyla Tutar (sola dayalı)
                ettn_elements = _create_ettn_and_words_section(subtotal, total_vat, ettn)
                for element in ettn_elements:
                    elements.append(element)
                elements.append(Spacer(1, 8*mm))
                
                # Footer - Banka Bilgileri (tüm bankalar)
                try:
                    banks = db_manager.fetch_all("SELECT bank_name, account_holder, iban FROM banks ORDER BY is_default DESC, bank_name")
                    
                    if banks:
                        elements.append(Paragraph("<b>Banka Bilgileri</b>", styles['styleB']))
                        for bank in banks:
                            bank_name, account_holder, iban = bank
                            bank_text = f"Banka: {bank_name}<br/>Hesap Sahibi: {account_holder}<br/>IBAN: {iban}"
                            elements.append(Paragraph(bank_text, styleN))
                            elements.append(Spacer(1, 2*mm))
                        elements.append(Spacer(1, 2*mm))
                except Exception as e:
                    # Fallback: Eski tek banka sistemi
                    bank_info_parts = [
                        f"Banka: {comp_info.get('bank_name')}" if comp_info.get('bank_name') else None,
                        f"Hesap Sahibi: {comp_info.get('bank_account_holder')}" if comp_info.get('bank_account_holder') else None,
                        f"IBAN: {comp_info.get('bank_iban')}" if comp_info.get('bank_iban') else None,
                    ]
                    bank_info_text = "<br/>".join(filter(None, bank_info_parts))
                    if bank_info_text:
                        elements.append(Paragraph("<b>Banka Bilgileri</b>", styles['styleB']))
                        elements.append(Paragraph(bank_info_text, styleN))
                        elements.append(Spacer(1, 4*mm))
                
                doc.build(elements)
            except Exception as e:
                logging.error(f"Fatura PDF'i oluşturulurken hata: {e}", exc_info=True)
        # PDF'leri birleştir
        merger = PdfMerger()
        for temp_path in temp_files:
            merger.append(temp_path)
        merger.write(file_path)
        merger.close()
        # Geçici dosyaları sil
        for temp_path in temp_files:
            try:
                os.remove(temp_path)
            except Exception:
                pass
        logging.info(f"Birleştirilmiş fatura başarıyla oluşturuldu: {file_path}")
        return True
    except Exception as e:
        logging.error(f"Birleştirilmiş fatura oluşturulurken hata: {e}", exc_info=True)
        return False

def create_combined_invoice_pdf(customer_name: str, invoices_data: List[Dict[str, Any]], file_path: str) -> bool:
    """
    Birden fazla faturayı tek bir fatura içerisinde birleştirir.
    Tüm ürün/hizmetler tek tabloda gösterilir.
    """
    try:
        from utils.database import db_manager
        import logging
        
        if not invoices_data:
            return False
            
        # İlk faturadan temel bilgileri al
        first_invoice = invoices_data[0]
        
        # Şirket bilgilerini al
        company_info = first_invoice.get('company_info')
        if not company_info:
            company_info = {
                'name': db_manager.get_setting('company_name', 'Firma Adı'),
                'address': db_manager.get_setting('company_address', 'Adres Bilgisi Yok'),
                'phone': db_manager.get_setting('company_phone', 'Telefon Bilgisi Yok'),
                'tax_office': db_manager.get_setting('company_tax_office', ''),
                'tax_id': db_manager.get_setting('company_tax_id', ''),
                'email': db_manager.get_setting('company_email', ''),
                'logo_path': db_manager.get_setting('company_logo_path', ''),
            }
        
        # Müşteri bilgilerini al
        customer_info = first_invoice.get('customer_info')
        if not customer_info:
            customer_info = {'name': customer_name}
        
        # Tüm ürün/hizmetleri birleştir
        all_items = []
        total_invoice_count = len(invoices_data)
        
        for idx, invoice in enumerate(invoices_data, 1):
            items = invoice.get('items', [])
            # Her faturanın ürünlerine fatura numarası bilgisi ekle
            for item in items:
                item_copy = item.copy()
                item_copy['invoice_ref'] = f"F-{invoice.get('id', 'N/A')}"
                all_items.append(item_copy)
        
        # Aynı hizmetleri birleştir (miktar ve fatura referanslarını topla)
        all_items = _merge_duplicate_items(all_items)
        
        # Birleşik fatura verisi oluştur
        combined_invoice_data = {
            'id': f"BİRLEŞİK-{'-'.join([str(inv.get('id', '')) for inv in invoices_data])}",
            'invoice_date': first_invoice.get('invoice_date'),
            'customer_info': customer_info,
            'company_info': company_info,
            'items': all_items,
            'vat_rate': first_invoice.get('vat_rate', '20.0'),
            'currency': first_invoice.get('currency', 'TL'),
            'is_combined': True,
            'original_invoice_count': total_invoice_count
        }
        
        # PDF oluştur
        doc = SimpleDocTemplate(file_path, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
        elements = []
        styles = get_professional_styles()
        styleN, styleT = styles["styleN"], styles["styleT"]
        
        # Header
        elements.append(_create_document_header(company_info, customer_info))
        elements.append(Spacer(1, 8*mm))
        
        # Fatura bilgileri
        try:
            invoice_date_obj = datetime.strptime(combined_invoice_data.get('invoice_date'), '%Y-%m-%d')
            invoice_date_str = invoice_date_obj.strftime('%d.%m.%Y')
        except (ValueError, TypeError):
            invoice_date_str = combined_invoice_data.get('invoice_date', 'N/A')
        
        invoice_no = combined_invoice_data.get('id')
        details_table = Table([
            [Paragraph("<b>BİRLEŞİK FATURA</b>", styleT), 
             Paragraph(f"Fatura No: {invoice_no}<br/>Tarih: {invoice_date_str}<br/>Birleşik Fatura Sayısı: {total_invoice_count}", styleN)]
        ], colWidths=[90*mm, 90*mm])
        details_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), 
            ('ALIGN', (1,0), (1,0), 'RIGHT')
        ]))
        elements.append(details_table)
        elements.append(Spacer(1, 8*mm))
        
        # Ürün/Hizmet tablosu (fatura referansı ile)
        vat_rate = Decimal(combined_invoice_data.get('vat_rate', '20.0'))
        original_currency = combined_invoice_data.get('currency', 'TL')
        items_table, currency_totals = _create_combined_items_table(all_items, vat_rate, original_currency)
        elements.append(items_table)
        elements.append(Spacer(1, 4*mm))
        
        # Para Birimi Bazında Toplamlar
        totals_table, grand_total_tl = _create_currency_totals_table(currency_totals, vat_rate)
        elements.append(totals_table)
        elements.append(Spacer(1, 8*mm))
        
        # eETTN ve Yazıyla Tutar (sola dayalı)
        ettn = combined_invoice_data.get('ettn', None)
        ettn_elements = _create_ettn_and_words_section_currency(grand_total_tl, ettn)
        for element in ettn_elements:
            elements.append(element)
        elements.append(Spacer(1, 8*mm))
        
        # Footer - Banka Bilgileri
        try:
            banks = db_manager.fetch_all("SELECT bank_name, account_holder, iban FROM banks ORDER BY is_default DESC, bank_name")
            
            if banks:
                elements.append(Paragraph("<b>Banka Bilgileri</b>", styles['styleB']))
                for bank in banks:
                    bank_name, account_holder, iban = bank
                    bank_text = f"Banka: {bank_name}<br/>Hesap Sahibi: {account_holder}<br/>IBAN: {iban}"
                    elements.append(Paragraph(bank_text, styleN))
                    elements.append(Spacer(1, 2*mm))
                elements.append(Spacer(1, 2*mm))
        except Exception as e:
            # Fallback: Eski tek banka sistemi
            bank_info_parts = [
                f"Banka: {company_info.get('bank_name')}" if company_info.get('bank_name') else None,
                f"Hesap Sahibi: {company_info.get('bank_account_holder')}" if company_info.get('bank_account_holder') else None,
                f"IBAN: {company_info.get('bank_iban')}" if company_info.get('bank_iban') else None,
            ]
            bank_info_text = "<br/>".join(filter(None, bank_info_parts))
            if bank_info_text:
                elements.append(Paragraph("<b>Banka Bilgileri</b>", styles['styleB']))
                elements.append(Paragraph(bank_info_text, styleN))
                elements.append(Spacer(1, 4*mm))
        
        doc.build(elements)
        logging.info(f"Birleşik fatura başarıyla oluşturuldu: {file_path}")
        return True
        
    except Exception as e:
        logging.error(f"Birleşik fatura oluşturulurken hata: {e}", exc_info=True)
        return False

def create_table_report_pdf(title: str, headers: List[str], data: List[List[Any]], file_path: str) -> bool:
    """
    Verilen başlık, başlık satırları ve verilerle yatay (landscape) bir tablo raporu PDF'i oluşturur.
    """
    try:
        doc = SimpleDocTemplate(file_path, pagesize=landscape(A4), rightMargin=inch, leftMargin=inch, topMargin=inch, bottomMargin=inch)
        elements = []
        styles = get_professional_styles()
        font_name, font_name_bold = get_font_names()

        # Başlık
        elements.append(Paragraph(title, styles['styleT']))
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(f"Rapor Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}", styles['styleN']))
        elements.append(Spacer(1, 12))

        # Tablo verilerini ve stillerini hazırla
        table_data = [headers] + [[Paragraph(str(cell), styles['styleN']) for cell in row] for row in data]
        
        # Sütun genişliklerini ayarla
        num_columns = len(headers)
        page_width, _ = landscape(A4)
        available_width = page_width - 2 * inch
        col_widths = [available_width / num_columns] * num_columns

        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), font_name_bold),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
        ]))

        elements.append(table)
        doc.build(elements)
        logging.info(f"Tablo raporu başarıyla oluşturuldu: {file_path}")
        return True
    except Exception as e:
        logging.error(f"Tablo raporu oluşturulurken hata: {e}", exc_info=True)
        return False

# --- GERİYE DÖNÜK UYUMLULUK İÇİN ESKİ FONKSİYONLAR ---

def create_quote_form_pdf(data: Dict[str, Any], file_path: str) -> bool:
    """
    Fiyat teklifi PDF'i oluşturur (ReportLab ile A4 formatında).
    Görüntüdeki gibi detaylı, profesyonel format.
    """
    try:
        register_fonts()
        
        # PDF dokümanı oluştur
        doc = SimpleDocTemplate(
            file_path,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=15*mm,
            bottomMargin=20*mm
        )
        
        elements = []
        font_name, font_name_bold = get_font_names()
        
        # Stil tanımlamaları
        title_style = ParagraphStyle(
            'QuoteTitle',
            fontName=font_name_bold,
            fontSize=20,
            textColor=colors.HexColor('#003366'),
            alignment=TA_RIGHT,
            spaceAfter=3*mm
        )
        
        heading_style = ParagraphStyle(
            'QuoteHeading',
            fontName=font_name_bold,
            fontSize=12,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=3*mm,
            spaceBefore=5*mm
        )
        
        normal_style = ParagraphStyle(
            'QuoteNormal',
            fontName=font_name,
            fontSize=10,
            spaceAfter=2*mm
        )
        
        small_style = ParagraphStyle(
            'QuoteSmall',
            fontName=font_name,
            fontSize=9,
            spaceAfter=1*mm
        )
        
        # Veri çıkar
        comp_info = data.get('company_info', {})
        main_info = data.get('main_info', {})
        quote_items = data.get('quote_items', [])
        
        # 1. HEADER - Logo, Firma Bilgileri ve Başlık
        logo_path = comp_info.get('company_logo_path') or comp_info.get('logo_path', '')
        
        # Firma bilgileri metni
        company_name = comp_info.get('company_name', '')
        company_address = comp_info.get('company_address', '')
        company_phone = comp_info.get('company_phone', '')
        company_email = comp_info.get('company_email', '')
        company_tax_office = comp_info.get('company_tax_office', '')
        company_tax_id = comp_info.get('company_tax_id', '')
        
        company_info_text = f"""<b>{company_name}</b><br/>
{company_address}<br/>
Tel: {company_phone} | E-posta: {company_email}<br/>
Vergi Dairesi: {company_tax_office} | VKN: {company_tax_id}"""
        
        company_style = ParagraphStyle(
            'CompanyInfo',
            fontName=font_name,
            fontSize=9,
            textColor=colors.HexColor('#333333'),
            alignment=TA_LEFT,
            leading=12
        )
        
        if logo_path and os.path.exists(logo_path):
            try:
                logo_img = Image(logo_path, width=45*mm, height=18*mm)
                company_para = Paragraph(company_info_text, company_style)
                title_para = Paragraph("<b>Fiyat Teklifi</b>", title_style)
                
                # Logo + Firma Bilgileri sol, Başlık sağ
                left_content = Table([[logo_img], [company_para]], colWidths=[90*mm])
                left_content.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('TOPPADDING', (0, 1), (0, 1), 3*mm),
                ]))
                
                header_table = Table([[left_content, title_para]], colWidths=[100*mm, 70*mm])
                header_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                    ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
                    ('VALIGN', (0, 0), (-1, 0), 'TOP'),
                ]))
                elements.append(header_table)
            except Exception as e:
                logging.warning(f"Logo yüklenemedi: {e}")
                elements.append(Paragraph(company_info_text, company_style))
                elements.append(Spacer(1, 3*mm))
                elements.append(Paragraph("<b>Fiyat Teklifi</b>", title_style))
        else:
            # Logo yoksa sadece firma bilgileri ve başlık
            if company_name:
                elements.append(Paragraph(company_info_text, company_style))
                elements.append(Spacer(1, 3*mm))
            elements.append(Paragraph("<b>Fiyat Teklifi</b>", title_style))
        
        # Çizgi
        elements.append(Spacer(1, 2*mm))
        line = Table([['']],colWidths=[170*mm])
        line.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (-1, 0), 2, colors.black),
        ]))
        elements.append(line)
        elements.append(Spacer(1, 5*mm))
        
        # 2. MÜŞTERİ BİLGİLERİ
        elements.append(Paragraph("<b>Müşteri Bilgileri</b>", heading_style))
        elements.append(Spacer(1, 1*mm))
        
        customer_data = [
            [Paragraph(f"<b>İsim:</b> {main_info.get('customer_name', 'N/A')}", normal_style)],
            [Paragraph(f"<b>Telefon:</b> {main_info.get('customer_phone', 'N/A')}", normal_style)],
            [Paragraph(f"<b>Adres:</b> {main_info.get('customer_address', 'N/A')}", normal_style)],
            [Paragraph(f"<b>Cihaz:</b> {main_info.get('device_model', 'N/A')} (Seri No: {main_info.get('device_serial', 'N/A')})", normal_style)],
        ]
        
        customer_table = Table(customer_data, colWidths=[170*mm])
        customer_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(customer_table)
        elements.append(Spacer(1, 5*mm))
        
        # 3. TEKLİF KALEMLERİ
        elements.append(Paragraph("<b>Teklif Kalemleri</b>", heading_style))
        elements.append(Spacer(1, 2*mm))
        
        if quote_items:
            # Tablo başlıkları
            table_data = [[
                Paragraph("<b>Açıklama</b>", small_style),
                Paragraph("<b>Adet</b>", small_style),
                Paragraph("<b>Birim Fiyat</b>", small_style),
                Paragraph("<b>Toplam (TL)</b>", small_style)
            ]]
            
            grand_total = Decimal('0.00')
            
            for item in quote_items:
                desc = item.get('description', 'N/A')
                qty = Decimal(str(item.get('quantity', 0)))
                price = Decimal(str(item.get('unit_price', 0)))
                currency = item.get('currency', 'TL')
                total_tl = Decimal(str(item.get('total_tl', 0)))
                grand_total += total_tl
                
                table_data.append([
                    Paragraph(desc, small_style),
                    Paragraph(str(int(qty)), small_style),
                    Paragraph(f"{price:.2f} {currency}", small_style),
                    Paragraph(f"{total_tl:.2f} TL", small_style)
                ])
            
            # Toplam satırı
            table_data.append([
                Paragraph("<b>GENEL TOPLAM:</b>", small_style),
                "",
                "",
                Paragraph(f"<b>{grand_total:.2f} TL</b>", small_style)
            ])
            
            items_table = Table(table_data, colWidths=[80*mm, 25*mm, 35*mm, 30*mm])
            items_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8f9fa')),
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
                ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), font_name_bold),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
                ('LINEABOVE', (0, -1), (-1, -1), 2, colors.black),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            elements.append(items_table)
        
        elements.append(Spacer(1, 3*mm))
        elements.append(Paragraph("<i>* Fiyatlara KDV dahil değildir.</i>", small_style))
        elements.append(Spacer(1, 8*mm))
        
        # 4. MÜŞTERİ ONAYI BEKLENİYOR - Sade Metin
        elements.append(Paragraph("<b>Müşteri Onayı Bekleniyor</b>", heading_style))
        elements.append(Spacer(1, 2*mm))
        elements.append(Paragraph(
            "Değişmesi gereken parça/parçaların fiyatı sunulmuştur. "
            "Onay vermeniz durumunda onarım işlemi başlatılacaktır.",
            normal_style
        ))
        elements.append(Spacer(1, 2*mm))
        elements.append(Paragraph(
            "Onayınızı telefon, e-posta veya bizzat gelerek verebilirsiniz.",
            normal_style
        ))
        
        # PDF'i oluştur
        doc.build(elements)
        logging.info(f"Fiyat teklifi PDF'i başarıyla oluşturuldu: {file_path}")
        return True
        
    except Exception as e:
        logging.error(f"Teklif PDF'i oluşturulurken hata: {e}", exc_info=True)
        return False


def create_detailed_quote_pdf(data: Dict[str, Any], file_path: str) -> bool:
    """
    Detaylı teklif PDF'i oluşturur (reportlab kullanarak).
    Veri yapısı: {'company_info', 'main_info', 'quote_items', 'total_amount'}
    """
    try:
        doc = SimpleDocTemplate(file_path, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
        elements = []
        styles = get_professional_styles()
        styleN, styleT = styles["styleN"], styles["styleT"]

        comp_info = data.get('company_info', {})
        main_info = data.get('main_info', {})
        quote_items = data.get('quote_items', [])
        total_amount = data.get('total_amount', 0)

        # 1. Şirket Başlığı
        elements.append(_create_document_header(comp_info, main_info))
        elements.append(Spacer(1, 8*mm))

        # 2. Teklif Başlığı ve Detayları
        from datetime import datetime
        current_date = datetime.now().strftime('%d.%m.%Y')
        service_id = main_info.get('service_id', 'N/A')

        details_table = Table([
            [Paragraph("<b>FİYAT TEKLİFİ</b>", styleT),
             Paragraph(f"Teklif No: {service_id}<br/>Tarih: {current_date}", styleN)]
        ], colWidths=[90*mm, 90*mm])
        details_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('ALIGN', (1,0), (1,0), 'RIGHT')]))
        elements.append(details_table)
        elements.append(Spacer(1, 8*mm))

        # 3. Müşteri Bilgileri
        customer_info = [
            ["Müşteri Adı:", main_info.get('customer_name', '')],
            ["Adres:", main_info.get('customer_address', '')],
            ["Telefon:", main_info.get('customer_phone', '')],
            ["E-posta:", main_info.get('customer_email', '')],
        ]

        customer_table = Table(customer_info, colWidths=[30*mm, 150*mm])
        customer_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(customer_table)
        elements.append(Spacer(1, 8*mm))

        # 4. Cihaz Bilgileri
        device_info = [
            ["Cihaz Model:", main_info.get('device_model', '')],
            ["Seri Numarası:", main_info.get('serial_number', '')],
            ["Arıza Açıklaması:", main_info.get('problem_description', '')],
        ]

        device_table = Table(device_info, colWidths=[40*mm, 140*mm])
        device_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightblue),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(device_table)
        elements.append(Spacer(1, 8*mm))

        # 5. Teklif Kalemleri Tablosu
        if quote_items:
            table_data = [['Açıklama', 'Adet', 'Birim Fiyat', 'Toplam']]
            for item in quote_items:
                description = item.get('description', '')
                quantity = item.get('quantity', 0)
                unit_price = item.get('unit_price', 0)
                total = quantity * unit_price
                currency = item.get('currency', 'TL')

                table_data.append([
                    description,
                    f"{quantity}",
                    f"{unit_price:.2f} {currency}",
                    f"{total:.2f} {currency}"
                ])

            items_table = Table(table_data, colWidths=[80*mm, 20*mm, 40*mm, 40*mm])
            items_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
                ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), font_name_bold),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
                ('LINEABOVE', (0, -1), (-1, -1), 2, colors.black),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            elements.append(items_table)
        
        elements.append(Spacer(1, 3*mm))
        elements.append(Paragraph("<i>* Fiyatlara KDV dahil değildir.</i>", small_style))
        elements.append(Spacer(1, 8*mm))
        
        # 6. MÜŞTERİ ONAYI BEKLENİYOR - Sade Metin
        elements.append(Paragraph("<b>Müşteri Onayı Bekleniyor</b>", heading_style))
        elements.append(Spacer(1, 2*mm))
        elements.append(Paragraph(
            "Değişmesi gereken parça/parçaların fiyatı sunulmuştur. "
            "Onay vermeniz durumunda onarım işlemi başlatılacaktır.",
            normal_style
        ))
        elements.append(Spacer(1, 2*mm))
        elements.append(Paragraph(
            "Onayınızı telefon, e-posta veya bizzat gelerek verebilirsiniz.",
            normal_style
        ))
        
        # PDF'i oluştur
        doc.build(elements)
        logging.info(f"Detaylı teklif PDF'i başarıyla oluşturuldu: {file_path}")
        return True

    except Exception as e:
        logging.error(f"Detaylı teklif PDF'i oluşturulurken hata: {e}", exc_info=True)
        return False


def generate_cpc_order_pdf(data: Dict[str, Any], file_path: str) -> bool:
        """
        CPC sipariş çıktısı PDF'i oluşturur.
        
        Args:
            data: CPC sipariş verileri
            file_path: PDF dosyasının kaydedileceği yol
            
        Returns:
            bool: PDF oluşturma başarı durumu
        """
        try:
            register_fonts()
            
            # PDF dokümanı oluştur
            doc = SimpleDocTemplate(
                file_path,
                pagesize=A4,
                rightMargin=20*mm,
                leftMargin=20*mm,
                topMargin=20*mm,
                bottomMargin=20*mm
            )
            
            # Stil tanımlamaları
            styles = getSampleStyleSheet()
            
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontName='DejaVuSans-Bold',
                fontSize=14,
                spaceAfter=12,
                alignment=TA_LEFT,
                textColor=colors.darkblue
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontName='DejaVuSans-Bold',
                fontSize=12,
                spaceAfter=10,
                textColor=colors.darkblue
            )
            
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontName='DejaVuSans',
                fontSize=10,
                spaceAfter=6
            )
            
            bold_style = ParagraphStyle(
                'CustomBold',
                parent=styles['Normal'],
                fontName='DejaVuSans-Bold',
                fontSize=10,
                spaceAfter=6
            )
            
            # PDF içeriği
            content = []
            
            # Başlık
            content.append(Paragraph("CPC SİPARİŞ ÇIKTISI (BEDELSİZ ÇIKIŞ)", title_style))
            content.append(Spacer(1, 6*mm))
            
            # Şirket ve Müşteri bilgilerini yan yana koy
            # Sol taraf: Müşteri bilgileri, Sağ taraf: Logo + Şirket bilgileri
            customer = data.get('customer', {})
            company = data.get('company', {})
            
            # Sağ kolon için logo + şirket bilgileri hazırla
            right_column_content = []
            
            # Logo ekle (eğer varsa) - orantılı boyutlandırma
            try:
                logo_path = "kyocera logo.png"
                if os.path.exists(logo_path):
                    # Logo'yu orijinal oranını koruyarak boyutlandır
                    # Sadece genişlik belirle, yükseklik otomatik hesaplanır
                    logo = Image(logo_path)
                    logo.drawWidth = 38*mm  # Genişlik
                    logo.drawHeight = None  # Yükseklik otomatik (orantılı)
                    logo._restrictSize(38*mm, 22*mm)  # Maksimum boyutlar
                    
                    # Logo'yu ortalamak için tablo içine al
                    logo_table = Table([[logo]], colWidths=[80*mm], style=TableStyle([
                        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                        ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
                    ]))
                    right_column_content.append(logo_table)
                    right_column_content.append(Spacer(1, 2*mm))
            except Exception as e:
                # Hata durumunda basit logo ekle
                try:
                    logo = Image(logo_path, width=35*mm, height=18*mm)
                    logo_table = Table([[logo]], colWidths=[80*mm], style=TableStyle([
                        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                        ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
                    ]))
                    right_column_content.append(logo_table)
                    right_column_content.append(Spacer(1, 2*mm))
                except:
                    pass
            
            # Şirket bilgileri tablosu
            company_table = Table([
                ['Şirket:', company.get('name', '')],
                ['Adres:', company.get('address', '')],
                ['Telefon:', company.get('phone', '')],
                ['Email:', company.get('email', '')]
            ], colWidths=[20*mm, 60*mm], style=TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'DejaVuSans'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('FONTNAME', (0, 0), (0, -1), 'DejaVuSans-Bold'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            
            right_column_content.append(company_table)
            
            # İki kolonlu tablo oluştur
            header_data = [
                [Paragraph('<b>MÜŞTERİ BİLGİLERİ</b>', heading_style), 
                 Paragraph('<b>FİRMA BİLGİLERİ</b>', heading_style)],
                [
                    # Sol kolon - Müşteri
                    Table([
                        ['Müşteri Adı:', customer.get('name', '')],
                        ['Telefon:', customer.get('phone', '')],
                        ['Email:', customer.get('email', '')],
                        ['Adres:', customer.get('address', '')]
                    ], colWidths=[25*mm, 55*mm], style=TableStyle([
                        ('FONTNAME', (0, 0), (-1, -1), 'DejaVuSans'),
                        ('FONTSIZE', (0, 0), (-1, -1), 9),
                        ('FONTNAME', (0, 0), (0, -1), 'DejaVuSans-Bold'),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('LEFTPADDING', (0, 0), (-1, -1), 0),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                    ])),
                    
                    # Sağ kolon - Logo + Şirket
                    right_column_content
                ]
            ]
            
            header_table = Table(header_data, colWidths=[85*mm, 85*mm])
            header_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1),  5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            
            content.append(header_table)
            content.append(Spacer(1, 8*mm))
            
            # Sipariş bilgileri - daha kompakt
            order_info_data = [
                ['Sipariş No:', data.get('order_number', ''), 'Sipariş Tarihi:', data.get('order_date', '')],
                ['Sipariş Türü:', 'CPC - Bedelsiz Çıkış', '', '']
            ]
            
            order_info_table = Table(order_info_data, colWidths=[30*mm, 55*mm, 30*mm, 55*mm])
            order_info_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'DejaVuSans'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('FONTNAME', (0, 0), (0, -1), 'DejaVuSans-Bold'),
                ('FONTNAME', (2, 0), (2, 0), 'DejaVuSans-Bold'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            
            content.append(order_info_table)
            content.append(Spacer(1, 8*mm))
            
            # Cihaz bilgileri (varsa) - daha kompakt
            if 'device' in data:
                device = data['device']
                device_info = f"CİHAZ: {device.get('model', '')} | Seri: {device.get('serial', '')} | Tip: {device.get('type', '')} | Renk: {device.get('color_type', '')}"
                
                device_style = ParagraphStyle(
                    'DeviceInfo',
                    parent=styles['Normal'],
                    fontName='DejaVuSans-Bold',
                    fontSize=10,
                    spaceAfter=8,
                    textColor=colors.darkblue,
                    alignment=TA_CENTER
                )
                
                content.append(Paragraph(device_info, device_style))
                content.append(Spacer(1, 5*mm))
            
            # Lokasyon bilgileri (varsa) - yeni eklenen
            if 'location' in data:
                location = data['location']
                location_info = f"LOKASYON: {location.get('name', '')}"
                if location.get('address'):
                    location_info += f" | Adres: {location.get('address', '')}"
                if location.get('phone'):
                    location_info += f" | Tel: {location.get('phone', '')}"
                
                location_style = ParagraphStyle(
                    'LocationInfo',
                    parent=styles['Normal'],
                    fontName='DejaVuSans',
                    fontSize=9,
                    spaceAfter=8,
                    textColor=colors.darkgreen,
                    alignment=TA_CENTER
                )
                
                content.append(Paragraph(location_info, location_style))
                content.append(Spacer(1, 5*mm))
            
            # Sipariş kalemleri
            content.append(Paragraph('SİPARİŞ KALEMLERİ', heading_style))
            
            # Tablo başlıkları - daha dar kolonlar
            table_data = [['#', 'Ürün Adı', 'Parça No', 'Miktar', 'Durum', 'İşlem Açıklaması']]
            
            # Kalemleri ekle
            for i, item in enumerate(data.get('items', []), 1):
                table_data.append([
                    str(i),
                    item.get('product_name', ''),
                    item.get('part_number', ''),
                    str(item.get('quantity', 0)),
                    'Bedelsiz',
                    item.get('note', '')[:25] + '...' if len(item.get('note', '')) > 25 else item.get('note', '')
                ])
            
            # Toplam satırı
            table_data.append(['', '', f"Toplam: {data.get('total_quantity', 0)}", '', 'BEDELSİZ', ''])
            
            # Tablo oluştur - çerçevesiz tasarım
            items_table = Table(table_data, colWidths=[10*mm, 50*mm, 30*mm, 15*mm, 25*mm, 40*mm])
            items_table.setStyle(TableStyle([
                # Başlık satırı
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'DejaVuSans-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                
                # Başlık altına çizgi
                ('LINEBELOW', (0, 0), (-1, 0), 2, colors.darkblue),
                
                # Veri satırları
                ('FONTNAME', (0, 1), (-1, -2), 'DejaVuSans'),
                ('FONTSIZE', (0, 1), (-1, -2), 8),
                ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
                ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Tarih
                ('ALIGN', (3, 1), (3, -1), 'CENTER'),  # Seri No
                ('ALIGN', (5, 1), (5, -1), 'CENTER'),  # Durum
                ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
                
                # Toplam satırı
                ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
                ('FONTNAME', (0, -1), (-1, -1), 'DejaVuSans-Bold'),
                ('FONTSIZE', (0, -1), (-1, -1), 9),
                ('ALIGN', (0, -1), (-1, -1), 'CENTER'),
                
                # Toplam satırı üstüne çizgi
                ('LINEABOVE', (0, -1), (-1, -1), 1, colors.grey),
                
                # Genel - çerçeve kaldırıldı
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 2),
                ('RIGHTPADDING', (0, 0), (-1, -1), 2),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            
            content.append(items_table)
            content.append(Spacer(1, 8*mm))
            
            # Notlar - daha kompakt
            if data.get('notes'):
                content.append(Paragraph('NOTLAR', heading_style))
                content.append(Paragraph(data['notes'], normal_style))
                content.append(Spacer(1, 5*mm))
            
            # Önemli bilgi - daha küçük
            warning_style = ParagraphStyle(
                'Warning',
                parent=styles['Normal'],
                fontName='DejaVuSans-Bold',
                fontSize=10,
                textColor=colors.red,
                alignment=TA_CENTER,
                spaceAfter=8
            )
            
            content.append(Paragraph('⚠️ BU SİPARİŞ CPC SİSTEMİ KAPSAMINDA BEDELSİZ OLARAK STOKTAN ÇIKIŞI YAPILMIŞTIR ⚠️', warning_style))
            content.append(Spacer(1, 5*mm))
            
            # İmza alanları - daha kompakt
            signature_data = [
                ['Sipariş Veren:', '', 'Teslim Eden:'],
                ['', '', ''],
                ['Ad Soyad: ............................', '', 'Ad Soyad: ............................'],
                ['İmza: ............................', '', 'İmza: ............................'],
                ['Tarih: ............................', '', 'Tarih: ............................']
            ]
            
            signature_table = Table(signature_data, colWidths=[70*mm, 30*mm, 70*mm])
            signature_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'DejaVuSans'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('FONTNAME', (0, 0), (0, 0), 'DejaVuSans-Bold'),
                ('FONTNAME', (2, 0), (2, 0), 'DejaVuSans-Bold'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            
            content.append(signature_table)
            
            # PDF'i oluştur
            doc.build(content)
            
            logging.info(f"CPC sipariş PDF'i başarıyla oluşturuldu: {file_path}")
            return True
            
        except Exception as e:
            logging.error(f"CPC sipariş PDF'i oluşturulurken hata: {e}", exc_info=True)
            return False

def create_service_report_pdf(data: Dict[str, Any], file_path: str) -> bool:
    """
    Servis tamamlama raporu PDF'i oluşturur (ReportLab ile).
    
    Args:
        data: Servis verileri (get_full_service_form_data'dan gelen)
        file_path: PDF dosyasının kaydedileceği yol
        
    Returns:
        bool: PDF oluşturma başarı durumu
    """
    try:
        register_fonts()
        
        # PDF dokümanı oluştur
        doc = SimpleDocTemplate(
            file_path,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm
        )
        
        # Stil tanımlamaları
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName='DejaVuSans-Bold',
            fontSize=15,
            spaceAfter=8,
            alignment=TA_RIGHT,
            textColor=colors.darkblue
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontName='DejaVuSans-Bold',
            fontSize=11,
            spaceAfter=6,
            textColor=colors.darkblue
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontName='DejaVuSans',
            fontSize=10,
            spaceAfter=4
        )
        
        small_style = ParagraphStyle(
            'CustomSmall',
            parent=styles['Normal'],
            fontName='DejaVuSans',
            fontSize=9,
            spaceAfter=3
        )
        
        bold_style = ParagraphStyle(
            'CustomBold',
            parent=styles['Normal'],
            fontName='DejaVuSans-Bold',
            fontSize=10,
            spaceAfter=4
        )
        
        # PDF içeriği
        content = []
        
        # Servis bilgileri
        main_info = data.get('main_info', {})
        company_info = data.get('company_info', {})
        
        # Logo ve başlık aynı satırda
        logo_path = company_info.get('company_logo_path') or company_info.get('logo_path', '')
        logo_img = None
        title_text = Paragraph("SERVİS TAMAMLAMA RAPORU", title_style)
        
        if logo_path and os.path.exists(logo_path):
            try:
                logo_img = Image(logo_path, width=35*mm, height=18*mm)
                # Logo ve başlığı aynı satırda yan yana yerleştir
                header_table = Table([[logo_img, title_text]], colWidths=[50*mm, 120*mm])
                header_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                    ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
                    ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                    ('LEFTPADDING', (0, 0), (0, 0), 0),
                    ('RIGHTPADDING', (1, 0), (1, 0), 0),
                ]))
                content.append(header_table)
            except Exception:
                # Logo yüklenemezse sadece başlığı göster
                content.append(title_text)
        else:
            # Logo yoksa sadece başlığı göster
            content.append(title_text)
        
        content.append(Spacer(1, 4*mm))
        
        # Firma ve müşteri bilgileri
        # Firma bilgileri için içerik hazırla
        company_content = [
            Table([
                ['Firma:', Paragraph(company_info.get('company_name', ''), small_style)],
                ['Adres:', Paragraph(company_info.get('company_address', ''), small_style)],
                ['Telefon:', Paragraph(company_info.get('company_phone', ''), small_style)],
                ['Email:', Paragraph(company_info.get('company_email', ''), small_style)]
            ], colWidths=[20*mm, 60*mm], style=TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'DejaVuSans'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('FONTNAME', (0, 0), (0, -1), 'DejaVuSans-Bold'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
        ]
        
        # Müşteri bilgileri için içerik hazırla
        customer_info = data.get('main_info', {})
        customer_content = [
            Table([
                ['Müşteri:', Paragraph(customer_info.get('customer_name', ''), small_style)],
                ['Telefon:', Paragraph(customer_info.get('customer_phone', ''), small_style)],
                ['Adres:', Paragraph(customer_info.get('customer_address', ''), small_style)],
                ['Vergi No:', Paragraph(customer_info.get('customer_tax_id', ''), small_style)]
            ], colWidths=[20*mm, 60*mm], style=TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'DejaVuSans'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('FONTNAME', (0, 0), (0, -1), 'DejaVuSans-Bold'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
        ]
        
        header_data = [
            [company_content, customer_content]
        ]
        
        header_table = Table(header_data, colWidths=[85*mm, 85*mm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        
        content.append(header_table)
        content.append(Spacer(1, 4*mm))
        
        # Servis bilgileri
        service_info_data = [
            ['Servis No:', str(main_info.get('id', '')), 'Servis Tarihi:', main_info.get('created_date', '')],
            ['Cihaz Model:', main_info.get('device_model', ''), 'Seri No:', main_info.get('device_serial', '')],
            ['Teknisyen:', main_info.get('technician_name', ''), 'Durum:', 'ONARILDI'],
            ['Onarım Tarihi:', datetime.now().strftime('%d.%m.%Y %H:%M'), '', '']
        ]
        
        # Sayaç bilgileri varsa servis tablosuna ekle
        bw_counter = main_info.get('bw_counter')
        color_counter = main_info.get('color_counter')
        
        if bw_counter or color_counter:
            # Önceki sayaç bilgilerini çek
            try:
                from .database import db_manager
                device_id = main_info.get('device_id')
                current_service_id = main_info.get('id')
                if device_id and current_service_id:
                    prev_counters = db_manager.get_previous_counter_readings(device_id, current_service_id)
                    prev_bw = prev_counters.get('bw_counter')
                    prev_color = prev_counters.get('color_counter')
                    
                    if bw_counter:
                        if prev_bw:
                            service_info_data.append(['BW Sayaç:', f'Önceki: {prev_bw} | Son: {bw_counter}', '', ''])
                        else:
                            service_info_data.append(['BW Sayaç:', str(bw_counter), '', ''])
                    
                    if color_counter:
                        if prev_color:
                            service_info_data.append(['Renkli Sayaç:', f'Önceki: {prev_color} | Son: {color_counter}', '', ''])
                        else:
                            service_info_data.append(['Renkli Sayaç:', str(color_counter), '', ''])
            except Exception as e:
                logging.warning(f"Sayaç geçmişi çekilirken hata: {e}")
                # Hata durumunda mevcut sayaç bilgilerini göster
                if bw_counter:
                    service_info_data.append(['BW Sayaç:', str(bw_counter), '', ''])
                if color_counter:
                    service_info_data.append(['Renkli Sayaç:', str(color_counter), '', ''])
        
        service_info_table = Table(service_info_data, colWidths=[30*mm, 55*mm, 30*mm, 55*mm])
        service_info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'DejaVuSans'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 0), (0, -1), 'DejaVuSans-Bold'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('WORDWRAP', (1, 0), (1, -1), True),  # Metin taşmasını önle
            ('WORDWRAP', (3, 0), (3, -1), True),  # Metin taşmasını önle
        ]))
        
        content.append(Paragraph('SERVİS BİLGİLERİ', heading_style))
        content.append(service_info_table)
        content.append(Spacer(1, 4*mm))
        
        # Bildirilen Arıza
        content.append(Paragraph('BİLDİRİLEN ARIZA', heading_style))
        problem_description = main_info.get('problem_description', 'Arıza açıklaması bulunamadı.')
        content.append(Paragraph(problem_description, small_style))
        content.append(Spacer(1, 3*mm))
        
        # Yapılan İşlemler
        content.append(Paragraph('YAPILAN İŞLEMLER', heading_style))
        notes = main_info.get('notes', 'İşlem açıklaması bulunamadı.')
        content.append(Paragraph(notes, small_style))
        content.append(Spacer(1, 3*mm))
        
        # Teknisyen Raporu
        content.append(Paragraph('TEKNİSYEN RAPORU', heading_style))
        technician_report = main_info.get('technician_report', 'Teknisyen raporu bulunamadı.')
        content.append(Paragraph(technician_report, small_style))
        content.append(Spacer(1, 4*mm))
        
        # Kullanılan Parçalar (varsa)
        used_parts = data.get('quote_items', [])
        if used_parts:
            content.append(Paragraph('KULLANILAN PARÇALAR', heading_style))
            
            parts_data = [['Parça Adı', 'Miktar', 'Birim Fiyat', 'Toplam']]
            for part in used_parts:
                parts_data.append([
                    Paragraph(part.get('description', ''), normal_style),
                    str(part.get('quantity', 0)),
                    f"{part.get('unit_price', 0):.2f} {part.get('currency', 'TL')}",
                    f"{part.get('total_tl', 0):.2f} TL"
                ])
            parts_table = Table(parts_data, colWidths=[60*mm, 20*mm, 30*mm, 30*mm])
            parts_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'DejaVuSans-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('LEFTPADDING', (0, 0), (-1, -1), 2),
                ('RIGHTPADDING', (0, 0), (-1, -1), 2),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            
            content.append(parts_table)
            content.append(Spacer(1, 4*mm))
        
        # İmza alanı
        signature_data = [
            ['Teknisyen Adı:', '', 'Tarih:', '', 'İmza:'],
            ['', '', '', '', '']
        ]
        
        signature_table = Table(signature_data, colWidths=[30*mm, 40*mm, 20*mm, 30*mm, 40*mm])
        signature_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'DejaVuSans'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 0), (0, 0), 'DejaVuSans-Bold'),
            ('FONTNAME', (2, 0), (2, 0), 'DejaVuSans-Bold'),
            ('FONTNAME', (4, 0), (4, 0), 'DejaVuSans-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        content.append(Paragraph('ONAY', heading_style))
        content.append(signature_table)
        
        # PDF'i oluştur
        doc.build(content)
        
        logging.info(f"Servis raporu PDF'i başarıyla oluşturuldu: {file_path}")
        return True
        
    except Exception as e:
        logging.error(f"Servis raporu PDF'i oluşturulurken hata: {e}", exc_info=True)
        return False

def create_service_history_report_pdf(data: Dict[str, Any], file_path: str) -> bool:
    """
    Servis iş geçmişi raporu PDF'i oluşturur (ReportLab ile).
    
    Args:
        data: Servis raporu verileri
        file_path: PDF dosyasının kaydedileceği yol
        
    Returns:
        bool: PDF oluşturma başarı durumu
    """
    try:
        register_fonts()
        
        # PDF dokümanı oluştur (yatay sayfa)
        doc = SimpleDocTemplate(
            file_path,
            pagesize=landscape(A4),
            rightMargin=15*mm,
            leftMargin=15*mm,
            topMargin=15*mm,
            bottomMargin=15*mm
        )
        
        # Stil tanımlamaları
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontName='DejaVuSans-Bold',
            fontSize=16,
            spaceAfter=10,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        )
        
        heading_style = ParagraphStyle(
            'ReportHeading',
            parent=styles['Heading2'],
            fontName='DejaVuSans-Bold',
            fontSize=12,
            spaceAfter=8,
            textColor=colors.darkblue
        )
        
        normal_style = ParagraphStyle(
            'ReportNormal',
            parent=styles['Normal'],
            fontName='DejaVuSans',
            fontSize=9,
            spaceAfter=4
        )
        
        small_style = ParagraphStyle(
            'ReportSmall',
            parent=styles['Normal'],
            fontName='DejaVuSans',
            fontSize=8,
            spaceAfter=3
        )
        
        # PDF içeriği
        content = []
        
        # Başlık
        report_title = data.get('report_title', 'SERVİS İŞ GEÇMİŞİ RAPORU')
        content.append(Paragraph(report_title, title_style))
        content.append(Spacer(1, 5*mm))
        
        # Rapor bilgileri
        report_info = data.get('report_info', {})
        info_text = f"Rapor Dönemi: {report_info.get('date_range', '')} | Toplam Kayıt: {report_info.get('total_records', 0)} | Rapor Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        content.append(Paragraph(info_text, normal_style))
        content.append(Spacer(1, 5*mm))
        
        # İstatistikler (varsa)
        stats = data.get('statistics', {})
        if stats:
            content.append(Paragraph('RAPOR İSTATİSTİKLERİ', heading_style))
            
            stats_data = []
            for key, value in stats.items():
                # Eğer value zaten "Key: Value" formatındaysa, sadece değeri al
                if ':' in str(value) and key in str(value):
                    # "Toplam Servis: 5" -> "5" al
                    actual_value = str(value).split(':', 1)[1].strip()
                else:
                    actual_value = str(value)
                stats_data.append([key, actual_value])
            
            stats_table = Table(stats_data, colWidths=[100*mm, 50*mm])
            stats_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
                ('FONTNAME', (0, 0), (-1, -1), 'DejaVuSans'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            
            content.append(stats_table)
            content.append(Spacer(1, 8*mm))
        
        # Servis kayıtları tablosu
        content.append(Paragraph('SERVİS KAYITLARI', heading_style))
        content.append(Spacer(1, 3*mm))
        
        service_records = data.get('service_records', [])
        
        if service_records:
            # Tablo başlıkları
            headers = ['Tarih', 'Müşteri', 'Cihaz Model', 'Seri No', 'Teknisyen', 'Durum', 'İşlem Açıklaması']
            table_data = [headers]
            
            # Veri satırları
            for record in service_records:
                row = [
                    record.get('date', ''),
                    Paragraph(record.get('customer_name', ''), small_style),
                    Paragraph(record.get('device_model', ''), small_style),
                    record.get('serial_number', ''),
                    record.get('technician', ''),
                    record.get('status', ''),
                    Paragraph(record.get('description', ''), small_style)
                ]
                table_data.append(row)
            
            # Tablo oluştur
            col_widths = [25*mm, 40*mm, 35*mm, 25*mm, 30*mm, 25*mm, 60*mm]
            records_table = Table(table_data, colWidths=col_widths, repeatRows=1)
            
            # Tablo stili - temel stiller
            table_style = [
                # Başlık satırı
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'DejaVuSans-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                
                # Veri satırları
                ('FONTNAME', (0, 1), (-1, -1), 'DejaVuSans'),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
                ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Tarih
                ('ALIGN', (3, 1), (3, -1), 'CENTER'),  # Seri No
                ('ALIGN', (5, 1), (5, -1), 'CENTER'),  # Durum
                ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
                
                # Izgara
                ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
                
                # Kenar boşlukları
                ('LEFTPADDING', (0, 0), (-1, -1), 2),
                ('RIGHTPADDING', (0, 0), (-1, -1), 2),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]
            
            # Alternatif satır renkleri (dinamik olarak ekle)
            for i in range(1, len(table_data)):
                if i % 2 == 1:  # Tek numaralı satırlar (1, 3, 5...)
                    table_style.append(('BACKGROUND', (0, i), (-1, i), colors.whitesmoke))
            
            records_table.setStyle(TableStyle(table_style))
            
            content.append(records_table)
        else:
            content.append(Paragraph("Seçilen kriterlere uygun servis kaydı bulunamadı.", normal_style))
        
        content.append(Spacer(1, 10*mm))
        
        # Alt bilgi
        footer_text = "Bu rapor ProServis sistemi tarafından otomatik olarak oluşturulmuştur."
        content.append(Paragraph(footer_text, small_style))
        
        # PDF'i oluştur
        doc.build(content)
        
        logging.info(f"Servis iş geçmişi raporu PDF'i başarıyla oluşturuldu: {file_path}")
        return True
        
    except Exception as e:
        logging.error(f"Servis iş geçmişi raporu PDF'i oluşturulurken hata: {e}", exc_info=True)
        return False
