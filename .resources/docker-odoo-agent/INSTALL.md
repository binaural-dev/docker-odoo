# Instalación: agente de docker-odoo + micro_saas

Esta guía deja funcionando la gestión de instancias desde Odoo (`micro_saas`) contra un host con `docker-odoo`.

```
┌──────────── Host con docker-odoo ────────────┐
│                                              │
│  docker-odoo-agent (systemd/launchd, :9000)  │        ┌── Odoo con micro_saas ──┐
│    ├─ lee/escribe instances.json             │◄───────│  (mismo host o remoto)  │
│    ├─ ./odoo build, docker compose           │  HTTP  │  Settings: URL + token  │
│    └─ git clone/pull en src/custom/<slug>    │ +token └─────────────────────────┘
└──────────────────────────────────────────────┘
```

Solo el agente toca archivos y Docker. Odoo le pide cada operación por HTTP con un token.

---

## 1. Instalar el agente en el host

### Requisitos

El instalador revisa todo esto y avisa de lo que falte:

- El checkout de `docker-odoo` en el host: el agente viene dentro (`.resources/docker-odoo-agent`) y gestiona ese mismo checkout.
- Python 3.8 o superior. Si falta el módulo `venv` (en Ubuntu, `python3-venv`), el instalador lo instala.
- Docker con `docker compose` v2, y el usuario que instala dentro del grupo `docker`.
- En Linux, `sudo` solo para instalar el servicio systemd y, si hace falta, paquetes o reglas de firewall. En macOS no hace falta `sudo`.

### Ejecutar el instalador

Con el mismo usuario que administra `docker-odoo` (en la VM de pruebas, `binaural`), desde la raíz de `docker-odoo`:

```bash
./odoo agent install --check           # opcional: muestra qué haría, sin cambiar nada
./odoo agent install --token-name general-18
```

`./odoo agent install` ejecuta `.resources/docker-odoo-agent/install.sh` con los mismos flags. El agente gestiona el checkout que lo contiene; la ruta queda guardada en `var/agent.env`.

El script es **idempotente**: solo hace lo que falta, y se puede repetir cuando quieras. Estos son sus pasos:

| Paso | Qué revisa | Qué hace si falta |
|---|---|---|
| docker-odoo | ubica el checkout que contiene al agente (o el de `--docker-odoo`) y revisa `./odoo`, `.resources/generators` e `instances.json`; avisa si alguna instancia monta `docker.sock` o si quedan copias anteriores del agente | nada: solo informa |
| Python | versión ≥ 3.8 y módulo `venv` | instala `python3-venv` (apt/dnf) |
| Docker | `docker`, `docker compose`, acceso al daemon | nada: indica cómo agregar el usuario al grupo `docker` |
| Dependencias | `.venv` y si `requirements.txt` cambió | crea el venv o instala/actualiza FastAPI y Uvicorn |
| Configuración y datos | `var/` (permisos `700`), `var/agent.env`, permisos `600` del archivo de tokens | crea `var/`, escribe o actualiza `agent.env` y trae los tokens y el log de una instalación anterior (el clon separado `docker-odoo-agent` o `docker-odoo/.resources/secrets/`) |
| Servicio | Linux: unidad systemd `/etc/systemd/system/docker-odoo-agent.service`. macOS: LaunchAgent de launchd | la instala o actualiza, la deja arrancando sola y la (re)inicia si cambió su definición, las dependencias o el código |
| Salud | `GET /health` | falla con la orden para ver el log |
| Firewall | `ufw` y el puerto | abre el puerto solo con `--open-firewall` |
| Tokens | tokens activos | crea uno si no hay ninguno o si pides uno nuevo con `--token-name` |

Al terminar muestra la **URL** y el **token** que hay que copiar en Odoo.

> El token se muestra **una sola vez**. Si lo pierdes: `./odoo agent token revoke <nombre>` y vuelve a ejecutar `./odoo agent install --token-name <nombre>`.

### Opciones

| Opción | Uso |
|---|---|
| `--check` | Solo diagnostica y lista los cambios pendientes |
| `--token-name <nombre>` | Crea un token con ese nombre, si no existe ya uno activo |
| `--docker-odoo <ruta>` | Checkout de docker-odoo que se va a gestionar |
| `--port <n>` | Otro puerto (por defecto 9000, o el guardado en `var/agent.env`) |
| `--open-firewall` | Abre el puerto en `ufw` para acceso remoto |
| `--no-service` | No instala el servicio (por ejemplo, para desarrollo) |

### En tu Mac (entorno local)

Es el mismo comando. En macOS el instalador usa **launchd** en lugar de systemd:

```bash
cd ~/workspace/18/docker-odoo
./odoo agent install --token-name local-mac
```

- Instala un *LaunchAgent* de tu usuario en `~/Library/LaunchAgents/com.binaural.docker-odoo-agent.plist`. No necesita `sudo`, arranca solo al iniciar sesión y se reinicia si se cae.
- Le pasa al servicio el `PATH` donde están `docker` (Docker Desktop) y `git`. Sin eso, launchd no los encuentra.
- Log del servicio: `~/Library/Logs/docker-odoo-agent.log`.
- En Docker Desktop, la URL para los contenedores es la misma: `http://host.docker.internal:9000`. El agente ve esas llamadas como `127.0.0.1`.

Si prefieres no dejarlo como servicio: `./odoo agent install --no-service` y levántalo a mano cuando lo necesites con `.venv/bin/python -m agent serve` desde `.resources/docker-odoo-agent`.

En Linux sin systemd pasa lo mismo: el instalador prepara todo menos el servicio y muestra la orden para levantarlo a mano.

---

## 2. Configurar micro_saas en Odoo

1. Actualiza el módulo en la instancia que lo tenga (en la VM, `general-18`):
   ```bash
   ./odoo update general-18 -d <base> -m micro_saas
   ```
2. Entra con un usuario **administrador** a **Gestión de instancias > Ajustes** (en español, *Gestión de instancias > Ajustes*):
   - **Agent URL**
     - Odoo en el **mismo host** que el agente: `http://host.docker.internal:9000`
     - Odoo en **otro equipo**: `http://<ip-del-host>:9000`, o la URL HTTPS si lo publicaste detrás de nginx (ver sección 4)
   - **Agent Token**: el que mostró el instalador.
3. Pulsa **Test connection**. Debe responder `Conectado como '<nombre>' (permisos: read, write)`.
4. Pulsa **Import from instances.json** para traer las instancias, bases y repositorios existentes.

Desde ese momento el cron sincroniza cada minuto el estado de los contenedores.

---

## 3. Migrar una instancia que usaba el esquema de montajes

Si `general-18` (u otra instancia) tenía en `instances.json` el esquema anterior, con `docker-odoo` y `docker.sock` montados dentro del contenedor, ya no hace falta:

1. En `instances.json`, dentro de `overwrite_odoo_config` de esa instancia, borra `extra_volumes` (montaje del repo y de `/var/run/docker.sock`) y cualquier `host_repo_root`.
2. Regenera y reinicia:
   ```bash
   ./odoo build
   ./odoo restart general-18
   ```
3. Vuelve a ejecutar `./odoo agent install --check`: el aviso sobre `docker.sock` debe desaparecer.

Así ese contenedor deja de tener control sobre la VM.

---

## 4. Acceso desde entornos remotos

El agente acepta conexiones de cualquier origen, así que cualquier Odoo local o remoto puede usarlo. El acceso lo controla el token:

- Crea **un token por entorno** (`--token-name bp-qa`, `--token-name laptop-roque`...), para poder revocar uno sin afectar a los demás.
- Si ese entorno solo va a consultar (por ejemplo, un tablero), usa un token de solo lectura: `./odoo agent token create tablero --read-only`.
- Si `ufw` está activo: `./odoo agent install --open-firewall`.
- **Usa HTTPS fuera del host.** Por HTTP plano el token viaja legible por la red. Lo más simple es un server block en el nginx del host que haga `proxy_pass http://127.0.0.1:9000;` con certificado, y usar esa URL `https://...` en Odoo.

---

## 5. Operación

| Tarea | Orden |
|---|---|
| Estado del servicio | `./odoo agent status` |
| Activar / desactivar | `./odoo agent` (según el estado), o `./odoo agent on` / `./odoo agent off` |
| Log del servicio | `./odoo agent logs [n]` |
| Reiniciar | Linux: `sudo systemctl restart docker-odoo-agent` · macOS: `launchctl kickstart -k gui/$(id -u)/com.binaural.docker-odoo-agent` |
| Auditoría (quién llamó a qué) | `tail -f .resources/docker-odoo-agent/var/agent_audit.log` |
| Cambiar de puerto | `./odoo agent install --port <n>` (reinicia el servicio) |
| Listar tokens | `./odoo agent token list` |
| Revocar un token (efecto inmediato) | `./odoo agent token revoke <nombre>` |
| Actualizar el agente | `git pull` en docker-odoo y `./odoo agent install` (solo reinicia si cambió algo) |
| Desinstalar (Linux) | `sudo systemctl disable --now docker-odoo-agent && sudo rm /etc/systemd/system/docker-odoo-agent.service` |
| Desinstalar (macOS) | `launchctl bootout gui/$(id -u)/com.binaural.docker-odoo-agent; rm ~/Library/LaunchAgents/com.binaural.docker-odoo-agent.plist` |

## 6. Problemas frecuentes

| Síntoma en Odoo | Causa y solución |
|---|---|
| *The docker-odoo agent is not configured* | Faltan la URL o el token en Settings |
| *Could not reach the docker-odoo agent* | El servicio está caído (`systemctl status`), la URL es incorrecta o el firewall cierra el puerto. Desde el contenedor: `docker exec odoo-general-18 curl -s http://host.docker.internal:9000/health` |
| *rejected the request: Token inválido o revocado* | Token mal copiado o revocado: genera uno nuevo |
| *Demasiados intentos fallidos* | La IP quedó bloqueada 15 min tras 10 tokens inválidos. Espera, o reinicia el servicio |
| *El token no tiene el permiso 'write'* | Es un token `--read-only`: crea uno de lectura y escritura |
| *Ya hay un build en curso* | Solo se permite un `./odoo build` a la vez. Espera a que termine |
| El servicio no arranca (`203/EXEC` en Linux, o se reinicia en bucle en macOS) | Falta el venv: vuelve a ejecutar `./odoo agent install` y revisa `./odoo agent logs` |
| En macOS, *docker: command not found* en el log | Docker Desktop cambió de ruta: vuelve a ejecutar `./odoo agent install`, que recalcula el `PATH` del servicio |

Referencia de endpoints y del modelo de seguridad: [README.md](README.md).

## 7. Migrar desde el repo separado `docker-odoo-agent`

Si el agente estaba instalado desde un clon aparte (`binaural-dev/docker-odoo-agent`, al lado de `docker-odoo` o dentro de él), o como carpeta `docker-odoo/agent`:

1. Actualiza `docker-odoo` a una versión que incluya `.resources/docker-odoo-agent` y ejecuta `./odoo agent install`.
   - Copia los tokens y el log de auditoría de la instalación anterior a `.resources/docker-odoo-agent/var/`, así que **los tokens existentes siguen valiendo** y no hay que tocar Odoo.
   - Reemplaza la unidad de systemd o el LaunchAgent (tienen el mismo nombre) para que apunten a esta carpeta, y reinicia el servicio.
2. Verifica con `./odoo agent status` y borra la copia anterior. El instalador avisa mientras siga existiendo.
