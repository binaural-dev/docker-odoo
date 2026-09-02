# Generación reproducible del APK/AAB (TWA) de la app de ventas: `./odoo apk`

**Estado: implementado y verificado (2026-09-02).** Documento retroactivo —
describe un pipeline ya aplicado y probado end-to-end, no un cambio pendiente.

## Por qué

La app de ventas (PWA sobre una instancia Odoo) se distribuye como APK/AAB
Android firmado (Trusted Web Activity vía Bubblewrap). Hacerlo a mano exige
un toolchain pesado en el host (Node + `@bubblewrap/cli`, OpenJDK 17, Android
SDK + licencias, `click` de Python) y hornea el `version_code` dentro del
`start_url` — el mecanismo con el que la app reporta la versión instalada de
cada vendedor. Olvidar ese parámetro deja a esa gente invisible en el
catálogo. Todo eso ahora vive en una imagen Docker: el host solo necesita
Docker.

## Qué cambia

- `.resources/apk/Dockerfile` + `docker-compose.yml`: imagen con el toolchain
  completo (Node + `@bubblewrap/cli`, OpenJDK 17, Android SDK con
  `platform-tools`/`platforms;android-34 y 36`/`build-tools;34.0.0 y 36.1.0`
  con licencias aceptadas, Python + `click`). Arquitectura-agnóstica:
  - El JDK se resuelve por PATH/`javac`, nunca por ruta hardcodeada de
    arquitectura (BuildKit no siempre inyecta `TARGETARCH`).
  - Soporte arm64: AGP 8.x no publica aapt2 `linux-arm64` (siempre baja la
    variante x86_64 de Maven), que corre vía binfmt (Rosetta en Docker
    Desktop, qemu-user en Linux) → la imagen instala `libc6:amd64` +
    `libgcc-s1:amd64` + `libstdc++6:amd64` + `zlib1g:amd64`.
  - `$ANDROID_HOME/bin/sdkmanager` es un wrapper `sh` que exec al real de
    `cmdline-tools/latest`: Bubblewrap (1.x) solo busca `sdkmanager` en
    `<sdk>/tools/bin` o `<sdk>/bin`, y un symlink rompe el classpath del
    script (resuelve `lib/` por `$0`).
  - Caché de Gradle persistente (volumen `apk-gradle-cache` → `/root/.gradle`):
    la primera build descarga ~15 min; las siguientes la reusan.
- `scripts/odoo-apk` (Python + click, dos modos):
  - **Host** (sin click, solo stdlib): lee `pwa.json` de la raíz del repo,
    hace `docker compose build` + `run --rm` re-ejecutando el script adentro,
    y deja los artefactos en el host vía el volumen `.ignore/apk-build` →
    `/work`. `APK_STOREPASS` y el contenido de `pwa.json` se pasan por env.
  - **Contenedor** (`APK_IN_CONTAINER=1`): la build real con Bubblewrap
    (manifest → `twa-manifest.json` → `bubblewrap update` → parche del
    `build.gradle` → `bubblewrap build` → firma → `assetlinks.json`).
- `pwa.json` (gitignored) + `pwa.example.json` (trackeado, con datos de
  prueba): configuración por archivo para no repetir el comando largo.
  Precedencia: **flag CLI > env `APK_STOREPASS` > `pwa.json` > default**.
- Flag `--scheme` (http/https): Bubblewrap hornea `https://` en duro en el
  `launchUrl` del APK; con instancias locales por HTTP el script parchea el
  `build.gradle` generado para usar el scheme real. En HTTP la app NO corre
  como TWA fullscreen (Android exige HTTPS) — abre en pestaña/custom tab;
  sirve para testear el pipeline.
- `./odoo apk usb-install`: instala `adb` según el SO del host (macOS:
  Homebrew cask; Linux: `apt`/`snap` con sudo), espera el dispositivo
  autorizado por USB, instala la APK generada con `adb install -r` y abre la
  app. Si no hay APK (o `--rebuild`), la genera primero.
- Launcher `odoo`: passthrough directo del subcomando `apk` a
  `scripts/odoo-apk` ANTES de argparse (apio acepta flags que argparse no
  conoce, p.ej. `--scheme`, `--rebuild`).

## Impacto

- Verificado end-to-end en arm64 contra una instancia local real
  (`http://192.168.1.226:9001`, `com.binaural.maxcam.ventas`): APK firmado
  1MB + AAB + `assetlinks.json` en el host; `apksigner verify` OK; el
  fingerprint SHA-256 del assetlinks coincide con el certificado; `start_url`
  `/payments?app_version=1` horneado en `res/Wo.json` del APK; instalado en
  un Moto G84 por USB (`adb install -r`).
- El primer intento de la prueba real destapó 3 bugs de la imagen
  (TARGETARCH, symlink de sdkmanager, glibc multiarch) — documentados arriba.
- El setup del túnel dev (`use.devtunnels.ms`) quedó descartado: los túneles
  de VS Code redirigen a OAuth de GitHub salvo que se creen con acceso
  anónimo, y el contenedor no puede autenticarse.