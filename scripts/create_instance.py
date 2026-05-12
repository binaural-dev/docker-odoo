#!/usr/bin/env python3
import json
import sys
import os
import subprocess
from pathlib import Path

BASE_PATH = Path(__file__).resolve().parent.parent
INSTANCES_FILE = BASE_PATH / "instances.json"
CUSTOM_DIR = BASE_PATH / "src" / "custom"


def get_used_ports(data):
    return [
        inst["external_port"]
        for inst in data.get("instances", {}).values()
        if "external_port" in inst
    ]


def get_suggested_port(used_ports):
    return max(used_ports) + 1 if used_ports else 8069


def interactive_menu(prompt_text, options_list):
    """
    Muestra un menú interactivo. options_list es una lista de tuplas (numero, texto, valor_retorno).
    """

    def fallback_prompt():
        print(f"\n{prompt_text}")
        for num, text, _ in options_list:
            print(f"  {num}) {text}")
        while True:
            choice = input("Opción: ").strip()
            for num, text, val in options_list:
                if str(num) == choice:
                    return val
            print("❌ Opción inválida.")

    if not sys.stdin.isatty():
        return fallback_prompt()

    try:
        import tty
        import termios
    except ImportError:
        return fallback_prompt()

    def getch():
        fd = sys.stdin.fileno()
        try:
            old_settings = termios.tcgetattr(fd)
        except Exception:
            return sys.stdin.read(1)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                ch += sys.stdin.read(2)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

    current_idx = 0
    input_buffer = ""
    lines_to_clear = len(options_list)

    print(f"\n{prompt_text} (Usa las flechas, números y Enter para confirmar):")

    def render_menu():
        sys.stdout.write("\r")
        for i, (num, text, _) in enumerate(options_list):
            prefix = "❯ " if i == current_idx else "  "
            if i == current_idx:
                sys.stdout.write(f"\033[92m{prefix}{num}. {text}\033[0m\033[K\n")
            else:
                sys.stdout.write(f"{prefix}{num}. {text}\033[K\n")
        sys.stdout.write(f"Opción [ {input_buffer} ]: \033[K")
        sys.stdout.flush()

    sys.stdout.write("\033[?25l")
    try:
        render_menu()
        while True:
            ch = getch()
            if ch == "\x03":  # Ctrl+C
                raise KeyboardInterrupt
            elif ch in ("\r", "\n"):
                sys.stdout.write("\n")
                break
            elif ch == "\x1b[A":  # Arriba
                current_idx = (current_idx - 1) % len(options_list)
                input_buffer = ""
            elif ch == "\x1b[B":  #s Abajo
                current_idx = (current_idx + 1) % len(options_list)
                input_buffer = ""
            elif ch in ("\x7f", "\b"):  # Backspace
                input_buffer = input_buffer[:-1]
            elif len(ch) == 1 and ch.isdigit():
                input_buffer += ch
                try:
                    num_val = int(input_buffer)
                    for i, (num, text, _) in enumerate(options_list):
                        if num == num_val:
                            current_idx = i
                            break
                except ValueError:
                    pass

            sys.stdout.write(f"\033[{lines_to_clear}F")
            render_menu()

    except Exception:
        sys.stdout.write("\033[?25h\nOperación cancelada.\n")
        sys.exit(0)
    finally:
        sys.stdout.write("\033[?25h")

    return options_list[current_idx][2]


def is_ssh_url(url):
    return url.startswith("git@") or url.startswith("ssh://")


def create_instance(name, repo_url, branch, odoo_version):
    if not is_ssh_url(repo_url):
        print(
            "❌ Error: La URL del repositorio debe ser SSH (debe empezar con 'git@' o 'ssh://')."
        )
        print("💡 Ejemplo válido: git@github.com:usuario/repo.git")
        print(
            "💡 Las URLs que empiezan con 'http://' o 'https://' no están permitidas."
        )
        sys.exit(1)

    if not INSTANCES_FILE.exists():
        print("Error: instances.json no encontrado.")
        sys.exit(1)

    with open(INSTANCES_FILE, "r") as f:
        data = json.load(f)

    if name in data.get("instances", {}):
        print(f"Error: La instancia '{name}' ya existe en instances.json.")
        sys.exit(1)

    repo_path = CUSTOM_DIR / name
    if repo_path.exists():
        print(f"Advertencia: El directorio {repo_path} ya existe. Saltando clone.")
    else:
        print(f"Clonando repositorio {repo_url} (rama: {branch}) en {repo_path}...")
        try:
            subprocess.run(
                ["git", "clone", "-b", branch, repo_url, str(repo_path)], check=True
            )

            print(f"Inicializando submódulos para {name}...")
            subprocess.run(
                ["git", "submodule", "update", "--init", "--recursive"],
                cwd=str(repo_path),
                check=True,
            )
        except subprocess.CalledProcessError:
            print(
                "❌ Error al clonar el repositorio o sus submódulos. Verifica la URL, permisos de acceso o problemas de conexión."
            )
            print("Limpiando directorio incompleto...")
            import shutil

            if repo_path.exists():
                shutil.rmtree(repo_path)
            sys.exit(1)

    used_ports = get_used_ports(data)
    suggested_port = get_suggested_port(used_ports)

    while True:
        try:
            port_input = input(
                f"\nIngresa el puerto externo para la instancia [Sugerido: {suggested_port}]: "
            ).strip()
            if not port_input:
                next_port = suggested_port
            else:
                next_port = int(port_input)

            if next_port in used_ports:
                print(
                    f"❌ Error: El puerto {next_port} ya está ocupado por otra instancia."
                )
                print(f"💡 Sugerencia: Puedes usar el puerto {suggested_port}")
                continue
            break
        except ValueError:
            print("❌ Error: Por favor ingresa un número de puerto válido.")

    requested_config = f"{odoo_version}_default"
    available_configs = data.get("odoo_configs", {}).keys()

    if requested_config in available_configs:
        odoo_config = requested_config
    elif "default" in available_configs:
        odoo_config = "default"
    else:
        print(
            f"❌ Error: No existe la configuración '{requested_config}' ni 'default' en la sección odoo_configs del JSON."
        )
        sys.exit(1)

    addons_list = []

    major_version = odoo_version.split(".")[0]
    enterprise_folder = f"src/enterprise-{major_version}"
    if (BASE_PATH / enterprise_folder).exists():
        addons_list.append(enterprise_folder)
    else:
        addons_list.append("src/enterprise")

    addons_list.append(f"src/custom/{name}")

    gitmodules_path = repo_path / ".gitmodules"
    if gitmodules_path.exists():
        print(
            f"🔍 Archivo .gitmodules detectado. Extrayendo rutas de submódulos para el JSON..."
        )
        import configparser

        config_parser = configparser.ConfigParser()
        try:
            config_parser.read(gitmodules_path)
            for section in config_parser.sections():
                if "path" in config_parser[section]:
                    sub_path = config_parser[section]["path"]
                    addons_list.append(f"src/custom/{name}/{sub_path}")
        except Exception as e:
            print(
                f"⚠️ Advertencia: No se pudo parsear el .gitmodules automáticamente: {e}"
            )

    if "instances" not in data:
        data["instances"] = {}

    data["instances"][name] = {
        "odoo_version": odoo_version,
        "external_port": next_port,
        "database": "pg16",
        "odoo_config": odoo_config,
        "overwrite_odoo_config": {"addons": addons_list},
    }

    with open(INSTANCES_FILE, "w") as f:
        json.dump(data, f, indent=2)

    print(
        f"\n✅ Instancia '{name}' creada exitosamente en instances.json con el puerto {next_port}!"
    )

    print("\n🚀 Aplicando cambios automáticamente (stop -> build -> start)...")
    try:
        print("\n>> Ejecutando: ./odoo stop")
        subprocess.run(["./odoo", "stop", "all"], cwd=BASE_PATH, check=True)

        print("\n>> Ejecutando: ./odoo build")
        subprocess.run(["./odoo", "build"], cwd=BASE_PATH, check=True)

        print("\n>> Ejecutando: ./odoo start")
        subprocess.run(["./odoo", "start", "all"], cwd=BASE_PATH, check=True)

        print(
            f"\n🎉 ¡Instancia {name} lista y ejecutándose en http://localhost:{next_port}!\n"
        )
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error al ejecutar los comandos de Odoo: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("\n=== Creador de Instancias Odoo ===")

    name = sys.argv[1] if len(sys.argv) > 1 else ""
    while not name:
        name = input("📦 Ingresa el nombre de la instancia (ej. micliente): ").strip()

    repo_url = sys.argv[2] if len(sys.argv) > 2 else ""
    while not repo_url or not is_ssh_url(repo_url):
        if repo_url and not is_ssh_url(repo_url):
            print("❌ Error: La URL debe ser SSH (git@... o ssh://...)")
        repo_url = input("🔗 Ingresa la URL SSH del repositorio: ").strip()

    branch = sys.argv[3] if len(sys.argv) > 3 else ""
    while not branch:
        branch_options = [
            (1, "release", "release"),
            (2, "staging", "staging"),
            (3, "otra", "otra"),
        ]
        branch_choice = interactive_menu(
            "🌿 Selecciona la rama del repositorio", branch_options
        )

        if branch_choice == "otra":
            while not branch:
                branch = input("🌿 Ingresa el nombre de la rama: ").strip()
        else:
            branch = branch_choice

    odoo_version = sys.argv[4] if len(sys.argv) > 4 else ""
    while not odoo_version:
        version_options = [(1, "17.0", "17.0"), (2, "19.0", "19.0")]
        odoo_version = interactive_menu(
            "⚙️  Selecciona la versión de Odoo", version_options
        )

    create_instance(name, repo_url, branch, odoo_version)
