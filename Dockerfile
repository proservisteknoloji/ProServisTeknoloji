# ProServis - Teknik Servis Yönetim Sistemi
# Docker Container for Development and Build Environment

FROM python:3.12-slim

# Metadata
LABEL maintainer="Ümit Sağdıç"
LABEL version="2.3.0"
LABEL description="ProServis Teknik Servis Yönetim Sistemi - Development Container"

# Çalışma dizini
WORKDIR /app

# Sistem bağımlılıklarını kur
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Qt için gerekli paketler
    libgl1-mesa-glx \
    libglib2.0-0 \
    libxcb1 \
    libxcb-cursor0 \
    libxkbcommon0 \
    libxcb-xinerama0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libegl1 \
    libfontconfig1 \
    libdbus-1-3 \
    # ODBC için gerekli paketler
    unixodbc \
    unixodbc-dev \
    # Genel araçlar
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Microsoft ODBC Driver for SQL Server (Azure SQL için)
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/12/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*

# Python bağımlılıklarını kopyala ve kur
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# PyInstaller'ı kur (build için)
RUN pip install --no-cache-dir pyinstaller==6.3.0

# Uygulama dosyalarını kopyala
COPY . .

# Font dizinini oluştur ve fontları kopyala
RUN mkdir -p /usr/share/fonts/truetype/dejavu \
    && cp resources/fonts/*.ttf /usr/share/fonts/truetype/dejavu/ 2>/dev/null || true \
    && fc-cache -fv

# Ortam değişkenleri
ENV PYTHONUNBUFFERED=1
ENV QT_QPA_PLATFORM=offscreen
ENV PYTHONDONTWRITEBYTECODE=1

# Uygulama portunu expose et (gerekirse)
EXPOSE 8080

# Varsayılan komut
CMD ["python", "main.py"]
