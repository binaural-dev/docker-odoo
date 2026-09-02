# Toolchain para generar el APK/AAB de la app (TWA) con scripts/odoo-apk.
#
# Todo corre dentro de este contenedor: Node + @bubblewrap/cli, OpenJDK 17,
# Android SDK (cmdline-tools + platform-tools + platforms;android-34 +
# build-tools;34.0.0 con licencias aceptadas) y Python + click para el script.
# El host solo necesita Docker: scripts/odoo-apk levanta este contenedor,
# ejecuta la build adentro y los artefactos quedan en el host via el volumen
# montado en APK_BUILD_ROOT (/work).
#
# Build (solo la primera vez o al cambiar la toolchain):
#   docker compose -f .resources/apk/docker-compose.yml build

FROM python:3.12-slim-bookworm

# NOTA: JAVA_HOME NO se fija aqui. La ruta del JDK depende de la arquitectura
# (/usr/lib/jvm/java-17-openjdk-{amd64,arm64}) y TARGETARCH no siempre se
# inyecta en el build. sdkmanager usa java del PATH, y scripts/odoo-apk
# deriva el JDK en runtime (JAVA_HOME o javac del PATH).
#
# libc6:amd64 y amigos: AGP 8.x NO tiene aapt2 para linux-arm64 (siempre baja
# la variante x86_64 de Maven). En arm64 el binario corre via binfmt (Rosetta
# en Docker Desktop, qemu-user en Linux): hace falta el loader x86_64.
ENV DEBIAN_FRONTEND=noninteractive \
    ANDROID_HOME=/opt/android-sdk \
    ANDROID_SDK_ROOT=/opt/android-sdk \
    APK_BUILD_ROOT=/work \
    APK_IN_CONTAINER=1

RUN dpkg --add-architecture amd64 \
 && apt-get update \
 && apt-get install -y --no-install-recommends \
        openjdk-17-jdk-headless \
        nodejs npm curl unzip \
        libc6:amd64 libgcc-s1:amd64 libstdc++6:amd64 zlib1g:amd64 \
 && rm -rf /var/lib/apt/lists/*

RUN npm install -g @bubblewrap/cli

# Bubblewrap 1.x usa targetSdk/compileSdk 36 + build-tools 36.1.0: se
# preinstalan para que el build no los baje de nuevo en cada corrida.
RUN mkdir -p "$ANDROID_HOME/cmdline-tools" \
 && curl -fsSLo /tmp/cmdline-tools.zip \
        https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip \
 && unzip -q /tmp/cmdline-tools.zip -d /tmp/cmdline-tools-dir \
 && mv /tmp/cmdline-tools-dir/cmdline-tools "$ANDROID_HOME/cmdline-tools/latest" \
 && rm -rf /tmp/cmdline-tools.zip /tmp/cmdline-tools-dir \
 && yes | "$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" --licenses >/dev/null \
 && "$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" \
        "platform-tools" \
        "platforms;android-34" "platforms;android-36" \
        "build-tools;34.0.0" "build-tools;36.1.0" \
 && mkdir -p "$ANDROID_HOME/bin" \
 && printf '#!/bin/sh\nexec %s "$@"\n' \
        "$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" \
        > "$ANDROID_HOME/bin/sdkmanager" \
 && chmod +x "$ANDROID_HOME/bin/sdkmanager" \
 && rm -rf /tmp/*

RUN python3 -m pip install --no-cache-dir click

WORKDIR /work
