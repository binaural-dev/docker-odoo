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
ENV DEBIAN_FRONTEND=noninteractive \
    ANDROID_HOME=/opt/android-sdk \
    ANDROID_SDK_ROOT=/opt/android-sdk \
    APK_BUILD_ROOT=/work \
    APK_IN_CONTAINER=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        openjdk-17-jdk-headless \
        nodejs npm curl unzip \
 && rm -rf /var/lib/apt/lists/*

RUN npm install -g @bubblewrap/cli

RUN mkdir -p "$ANDROID_HOME/cmdline-tools" \
 && curl -fsSLo /tmp/cmdline-tools.zip \
        https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip \
 && unzip -q /tmp/cmdline-tools.zip -d /tmp/cmdline-tools-dir \
 && mv /tmp/cmdline-tools-dir/cmdline-tools "$ANDROID_HOME/cmdline-tools/latest" \
 && rm -rf /tmp/cmdline-tools.zip /tmp/cmdline-tools-dir \
 && yes | "$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" --licenses >/dev/null \
 && "$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" \
        "platform-tools" "platforms;android-34" "build-tools;34.0.0" \
 && ln -s "$ANDROID_HOME/cmdline-tools/latest/bin" "$ANDROID_HOME/bin" \
 && rm -rf /tmp/*

RUN python3 -m pip install --no-cache-dir click

WORKDIR /work
