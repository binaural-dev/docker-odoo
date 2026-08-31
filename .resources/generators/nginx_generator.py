"""
Generates nginx configuration for all Odoo instances.
Each instance gets its own server block listening on its external_port AND
on port 80 (subdomain routing via Host header).

Access modes:
  - http://localhost:PORT          (legacy, port-based)
  - http://inst_name.local:PORT    (port-based, sub-domain aware)
  - http://inst_name.local         (subdomain-based, port 80)

Cookie isolation across instances is achieved because each subdomain is a
distinct browser origin (different host), so session_id and CSRF cookies do
not bleed across instances.
"""

import os


ODOO_HTTP_PORT = 8069
ODOO_GEVENT_PORT = 8071
NGINX_HTTP_PORT = 80


def generate_nginx_config(base_path, config):
    """
    Generate .resources/nginx_configs/generated.conf with:
      - one server block per Odoo instance (dual-stack: external_port + 80)
      - one server block for pgAdmin (if enabled)
      - one server block for MailHog (if enabled)
    """
    blocks = []
    is_first = True

    for inst_name, inst_conf in config["instances"].items():
        external_port = inst_conf["external_port"]
        container_name = f"odoo-{inst_name}"
        blocks.append(
            _odoo_server_block(inst_name, external_port, container_name, is_first)
        )
        is_first = False

    pgadmin_conf = config.get("pgadmin", {})
    if pgadmin_conf.get("enabled", False):
        pg_port = pgadmin_conf.get("port", 5050)
        blocks.append(
            _generic_service_block(
                "pgadmin", pg_port, 80, "pgadmin", is_first
            )
        )
        is_first = False

    mailhog_conf = config.get("mailhog", {})
    if mailhog_conf.get("enabled", False):
        mh_port = mailhog_conf.get("http_port", 8025)
        # MailHog web UI listens on 8025 inside the container.
        blocks.append(
            _generic_service_block(
                "mailhog", mh_port, 8025, "mailhog", is_first,
                upstream_port=8025,
            )
        )
        is_first = False

    output_path = os.path.join(
        base_path, ".resources", "nginx_configs", "generated.conf"
    )
    with open(output_path, "w") as f:
        f.write("\n".join(blocks))
        f.write("\n")

    print(f"  nginx generated.conf generado ({len(blocks)} server block(s))")
    return output_path


def _listen_lines(port_a, port_b, is_default_server):
    """Build ``listen`` directives. The first block becomes the default_server
    on port 80 so unmatched Host headers don't trigger nginx warnings.
    """
    a_default = " default_server" if is_default_server else ""
    return [
        f"    listen {port_a}{a_default};",
        f"    listen {port_b};",
    ]


def _odoo_server_block(inst_name, external_port, container_name, is_first):
    listen_lines = _listen_lines(external_port, NGINX_HTTP_PORT, is_first)
    listen_block = "\n".join(listen_lines)
    return f"""# Instance: {inst_name} (port {external_port} | {inst_name}.local)
server {{
{listen_block}
    server_name {inst_name}.local localhost;

    resolver 127.0.0.11 valid=30s;

    client_max_body_size 10000M;
    client_body_buffer_size 10000M;

    proxy_read_timeout 7200s;
    proxy_send_timeout 7200s;
    proxy_connect_timeout 7200s;
    send_timeout 7200s;

    location / {{
        set $proxy_upstream_{ODOO_HTTP_PORT} http://{container_name}:{ODOO_HTTP_PORT};
        proxy_pass $proxy_upstream_{ODOO_HTTP_PORT};
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_read_timeout 7200s;
        proxy_send_timeout 7200s;
    }}

    location /websocket {{
        set $proxy_upstream_{ODOO_GEVENT_PORT} http://{container_name}:{ODOO_GEVENT_PORT};
        proxy_pass $proxy_upstream_{ODOO_GEVENT_PORT};
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_read_timeout 7200s;
        proxy_send_timeout 7200s;
    }}
}}
"""


def _generic_service_block(
    name, external_port, internal_port, container_name, is_first,
    upstream_port=None,
):
    """Build a server block for a non-Odoo service (pgAdmin, MailHog)."""
    listen_lines = _listen_lines(external_port, NGINX_HTTP_PORT, is_first)
    listen_block = "\n".join(listen_lines)
    upstream_port = upstream_port or internal_port
    return f"""# Service: {name} (port {external_port} | {name}.local)
server {{
{listen_block}
    server_name {name}.local localhost;

    resolver 127.0.0.11 valid=30s;

    client_max_body_size 10000M;
    client_body_buffer_size 10000M;

    location / {{
        set $proxy_upstream_{upstream_port} http://{container_name}:{upstream_port};
        proxy_pass $proxy_upstream_{upstream_port};
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""
