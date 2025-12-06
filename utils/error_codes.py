# utils/error_codes.py
"""
Kyocera ve diğer marka fotokopi makineleri arıza kodları veritabanı
"""

KYOCERA_ERROR_CODES = {
    "C0030": "PWB Sorunu Faks. Faks yazılımı ile işleme yazılım veya donanım sorunları nedeniyle devre dışı bırakılır.",
    "C0060": "Ana PWB Tür uyuşmazlığı hatası.",
    "C0070": "PWB uygunsuzluğu Algılama Sorunu Faks. Faks yazılımı ana PWB yazılımı ile uyumlu değildir.",
    "C0130": "Ana PWB EEPROM Yedekleme Bellek Aygıtı Sorunu. EEPROM yazılı veya okunamıyor.",
    "C0140": "Ana PWB EEPROM Yedekleme Bellek Veri Sorunu. EEPROM anormal okuma verileri.",
    "C0150": "Motor PWB EEPROM Yedekleme Bellek Aygıtı Sorunu. EEPROM yazılı veya okunamıyor.",
    "C0160": "Motor PWB EEPROM Yedekleme Bellek Veri Sorunu. EEPROM anormal okuma verileri.",
    "C0170": "Kopya Sorunu sayar. Bir sağlama hatası kopya sayaçlar için ana ve motor yedek anılar saptanır.",
    "C0180": "Makine numarası uyuşmazlığı hatası. Makine numarası ana ve motor PWBs üzerinde eşleşmiyor",
    "C0600": "Ana PWB DIMM hatalı Yüklendi.",
    "C0610": "Ana PWB DIMM hatası",
    "C0630": "DMA iletimi hatası. Belirli bir zaman süresi içinde tamamlanmadı.",
    "C0640": "Sabit Disk Sürücüsü erişilemiyor",
    "C0700": "İsteğe bağlı CF yedek uygun değildir.",
    "C0800": "Görüntü işleme sorunu. JAM05 iki kez tespit edilir.",
    "C1010": "Kaset 1 kaldırma Motor hatası. 12 saniye veya aşırı akım 500ms aşıyor.",
    "C1020": "Kaset 2 kaldırma Motor hatası. 12 saniye veya aşırı akım 500ms aşıyor.",
    "C2000": "Sürücü Motor Sorunu. Motor stabilizasyonu 6 saniye içinde tespit edilmez.",
    "C2250": "Ana Şarj Temizleyici Motor hatası.",
    "C2500": "Kağıt Besleme Motor hatası. Stabilizasyon 6 saniye içinde tespit değildir.",
    "C3100": "Tarayıcı Taşıma Sorunu. Tarayıcı ev pozisyonu tespit edilmedi.",
    "C3200": "Pozlama Lambası Sorunu. Lamba 5 saniye içinde eşik değerine ulaşmıyor.",
    "C3300": "CCD AGC Sorunu. AGC doğru giriş elde edilmez.",
    "C3500": "Tarayıcı ve SHD Arasında Haberleşme Hatası.",
    "C4000": "Poligon Motor Senkronizasyon sorunu. Motor 20 saniye içinde stabilize değil.",
    "C4010": "Poligon Motor Durağan Devlet Sorunu.",
    "C4200": "BD Durağan Devlet Sorunu.",
    "C5300": "Lamba Kırık Tel temizlenmesi. Kırık tel algılama 2 saniye boyunca algılanır.",
    "C6000": "Fuser Isıtıcı Arızası. Thermistor sıcaklık sensörü problemi. Thermistor1 10 saniye boyunca 70°C altında veya Thermistor2 40°C altında algılandı.",
    "C6020": "Anormal yüksek Termistör Sıcaklığı. 250°C veya üzeri tespit edildi.",
    "C6030": "Termistör Arası Hata. Termistör mola sinyali 1 saniye tespit edilir.",
    "C6050": "Anormal düşük Termistör Sıcaklığı. 80°C veya daha az 1 saniye tespit edilir.",
    "C6400": "Sıfır Çapraz Sinyal Hatası. Sıfır çapraz sinyal 3 saniye içinde gelmedi.",
    "C6410": "Fuser Unit Bağlantı Sorunu. Fuser ünitesi takılı değil.",
    "C6420": "Fuser Unit Sigorta Kesme Sorunu.",
    "C7300": "Toner Kabı Sorunu. Toner seviyesi tespit edilmiyor.",
    "C7400": "Geliştirme Ünitesi Bağlantı Sorunu. Geliştirme ünitesi takılı değil.",
    "C7410": "Drum Ünitesi Bağlantı Sorunu. Drum ünitesi takılı değil.",
    "C7800": "Dış Termistör Tel Kopuk. Çevre sensörü 4.5V veya üzeri.",
    "C7810": "Kısa devre Dış Termistör. Giriş değeri 0.5V veya daha az.",
    "C7900": "EEPROM hatası Drum. Okuma veya yazma yapılamaz.",
    "C7910": "EEPROM Hatası Geliştirme. Okuma veya yazma yapılamaz.",
    "C8800": "DF-710 Haberleşme Sorunu. İletişim hatası.",
    "CF000": "Çalıştırma Paneli PWB İletişim Hatası / Sistem Hatası.",
    "CF010": "Ana PWB Checksum Hatası / Sistem Hatası.",
    "CF020": "Bellek Sağlama Toplamı Hatası / İşletim Sistemi Hatası.",
    "CF030": "Ana PWB Sistem Hatası.",
    "CF040": "Motor PWB İletişim Hatası.",
    "CF041": "Tarayıcı PWB İletişim Hatası.",
    "CF050": "Motor ROM Checksum Hatası.",
    "CF060": "Motor RAM Hatası.",
    "CF070": "Flash ROM hatası.",
    "CF14F": "Güç Kaynağı İkincil Yan Hata. Güç kaynağı kararsız.",
    "CF610": "Sistem Başlangıç Hatası.",
    "CF620": "Sistem hatası. Olay verileri elde hatası.",
    "CFB30": "Ana EEPROM Firmware Uyumsuz Seviye.",
    "CFB31": "Ana EEPROM Bozuk Firmware.",
    "CFB32": "Panel Hatası. Başlatma komutu zaman aşımı.",
    "CFB33": "Panel Hatası. Kontrolör ile bağlantı koptu.",
    "F000": "Çalıştırma Paneli PWB İletişim Hatası.",
    "F010": "Ana PWB Checksum Hatası.",
    "F020": "Bellek Sağlama Toplamı Hatası.",
    "F030": "Ana PWB Sistem Hatası.",
    "F040": "Motor PWB İletişim Hatası.",
    "F041": "Tarayıcı PWB İletişim Hatası.",
}

# Çözüm önerileri
KYOCERA_SOLUTIONS = {
    "C6000": {
        "nedenler": [
            "Thermistor 1 veya 2 arızası",
            "Fuser lamba arızası",
            "Termostat arızası",
            "Kablolama problemi",
            "Ana kart sorunu"
        ],
        "cozum": [
            "1. Makineyi kapatın ve 30 dakika soğumaya bırakın",
            "2. Fuser ünitesini çıkarın",
            "3. Thermistor bağlantılarını kontrol edin",
            "4. Multimetre ile thermistor direncini ölçün (normal: 100-200 kΩ oda sıcaklığında)",
            "5. Fuser lambalarını görsel olarak kontrol edin",
            "6. Arızalı parçayı değiştirin",
            "7. Test baskısı yapın"
        ],
        "parcalar": [
            "Thermistor 1",
            "Thermistor 2",
            "Fuser lamba",
            "Fuser ünitesi (ciddi hasarda)"
        ],
        "onleyici": [
            "Düzenli fuser temizliği yapın",
            "Voltaj regülatörü kullanın",
            "Periyodik bakım yapın",
            "Orijinal parça kullanın"
        ]
    },
    "C6020": {
        "nedenler": [
            "Thermistor arızası",
            "Aşırı ısınma",
            "Termostat arızası",
            "Havalandırma sorunu"
        ],
        "cozum": [
            "1. ACİL! Makineyi hemen kapatın",
            "2. Fuser ünitesini soğumaya bırakın (minimum 1 saat)",
            "3. Havalandırma fanını kontrol edin",
            "4. Thermistor bağlantılarını kontrol edin",
            "5. Termostatı test edin",
            "6. Gerekirse fuser ünitesini değiştirin"
        ],
        "parcalar": [
            "Thermistor",
            "Termostat",
            "Fuser ünitesi",
            "Havalandırma fanı"
        ],
        "onleyici": [
            "Havalandırma deliklerini temiz tutun",
            "Makineyi serin ortamda kullanın",
            "Aşırı yüklemeden kaçının"
        ]
    },
    "C7300": {
        "nedenler": [
            "Toner seviye sensörü arızası",
            "Toner kartuşu hatalı takılmış",
            "Toner chip sorunu",
            "Kablolama problemi"
        ],
        "cozum": [
            "1. Toner kartuşunu çıkarın ve tekrar takın",
            "2. Toner chip'ini temizleyin",
            "3. Toner seviye sensörünü kontrol edin",
            "4. Yeni toner kartuşu deneyin",
            "5. Sensör kablolarını kontrol edin"
        ],
        "parcalar": [
            "Toner kartuşu",
            "Toner seviye sensörü",
            "Toner chip"
        ],
        "onleyici": [
            "Orijinal toner kullanın",
            "Toneri doğru takın",
            "Düzenli temizlik yapın"
        ]
    }
}


def get_error_description(brand: str, error_code: str) -> dict:
    """
    Arıza kodu için açıklama ve çözüm önerisi döndürür.
    
    Args:
        brand: Marka adı (Kyocera, Canon, vb.)
        error_code: Arıza kodu (C6000, F040, vb.)
    
    Returns:
        dict: Açıklama, nedenler, çözüm, parçalar içeren sözlük
    """
    error_code = error_code.upper().strip()
    
    if brand == "Kyocera":
        description = KYOCERA_ERROR_CODES.get(error_code)
        solution = KYOCERA_SOLUTIONS.get(error_code)
        
        if description:
            result = {
                "kod": error_code,
                "aciklama": description,
                "bulundu": True
            }
            
            if solution:
                result.update({
                    "nedenler": solution.get("nedenler", []),
                    "cozum": solution.get("cozum", []),
                    "parcalar": solution.get("parcalar", []),
                    "onleyici": solution.get("onleyici", []),
                    "detayli": True
                })
            else:
                result["detayli"] = False
            
            return result
    
    return {
        "kod": error_code,
        "bulundu": False,
        "aciklama": "Arıza kodu veritabanında bulunamadı."
    }


def format_error_response(error_data: dict) -> str:
    """
    Arıza kodu verisini okunabilir formata çevirir.
    
    Args:
        error_data: get_error_description'dan dönen veri
    
    Returns:
        str: Formatlanmış metin
    """
    if not error_data.get("bulundu"):
        return f"❌ {error_data['kod']} kodu veritabanında bulunamadı.\n\nYapay zeka analizi için 'Sor' butonunu kullanabilirsiniz."
    
    output = f"✅ KYOCERA {error_data['kod']} ARIZA KODU\n\n"
    output += f"📋 AÇIKLAMA:\n{error_data['aciklama']}\n\n"
    
    if error_data.get("detayli"):
        output += "🔍 OLASI NEDENLER:\n"
        for i, neden in enumerate(error_data.get("nedenler", []), 1):
            output += f"  {i}. {neden}\n"
        output += "\n"
        
        output += "🔧 ÇÖZÜM ADIMLARI:\n"
        for adim in error_data.get("cozum", []):
            output += f"  {adim}\n"
        output += "\n"
        
        if error_data.get("parcalar"):
            output += "🛠️ DEĞİŞTİRİLECEK PARÇALAR:\n"
            for parca in error_data["parcalar"]:
                output += f"  • {parca}\n"
            output += "\n"
        
        if error_data.get("onleyici"):
            output += "⚠️ ÖNLEYİCİ TEDBİRLER:\n"
            for tedbir in error_data["onleyici"]:
                output += f"  • {tedbir}\n"
    else:
        output += "💡 Detaylı çözüm için yapay zeka analizi kullanabilirsiniz."
    
    return output
