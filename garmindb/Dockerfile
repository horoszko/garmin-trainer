# oficjalne repo https://github.com/tcgoetz/GarminDB
# TEN DOCKERFILE DOTYCZY WERSJI 3.9 KTORA PATCHUJEMY ABY POBIERANA BAZADANYCH BYLA BARDZIEJ AKTUALNA
# PO AKTUALIZACJI WRÓC DO WERSJI BEZ PATCHA.

FROM python:3.12-slim

# Łatwa możliwość wyłączenia patcha GarminDB #318.
# Przy oficjalnej poprawce można ustawić false.
ARG APPLY_GARMINDB_TODAY_PATCH=true

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Klonujemy oficjalne repo GarminDB
RUN git clone https://github.com/tcgoetz/GarminDB.git .

# Oryginalny patch:
# https://github.com/tcgoetz/GarminDB/pull/318
# Fix off-by-one preventing download of today's data
COPY patches/garmindb-today.patch /tmp/garmindb-today.patch

RUN if [ "$APPLY_GARMINDB_TODAY_PATCH" = "true" ]; then \
        if git apply --check /tmp/garmindb-today.patch; then \
            echo "Applying GarminDB PR #318 - include today's data"; \
            git apply /tmp/garmindb-today.patch; \
        elif git apply --reverse --check /tmp/garmindb-today.patch; then \
            echo "GarminDB PR #318 appears to be already included upstream - skipping patch"; \
        else \
            echo "ERROR: GarminDB PR #318 patch does not match this GarminDB version"; \
            exit 1; \
        fi; \
    else \
        echo "GarminDB PR #318 patch disabled"; \
    fi

# Instalujemy już spatchowaną wersję GarminDB.
# Dzięki temu również /usr/local/bin/garmindb_cli.py
# powstanie ze zmodyfikowanego kodu.
RUN pip install --no-cache-dir .

# Katalog na bazy SQLite
VOLUME ["/root/.GarminDb"]

CMD ["garmindb_cli.py", "--help"]
