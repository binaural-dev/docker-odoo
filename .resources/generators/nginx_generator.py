"""
Generates nginx configuration for all Odoo instances.
Each instance gets its own server block listening on its external_port,
proxying to the corresponding Odoo container on internal ports 8069/8071.
"""

import os


ODOO_HTTP_PORT = 8069
ODOO_GEVENT_PORT = 8071

def generate_nginx_config(base_path, config):
    """
    Generate .resources/nginx_configs/generated.conf with a server block
    per instance.
    """
    blocks = []

    for inst_name, inst_conf in config["instances"].items():
        external_port = inst_conf["external_port"]
        container_name = f"odoo-{inst_name}"
        blocks.append(
            _server_block(inst_name, external_port, container_name)
        )

    output_path = os.path.join(
        base_path, ".resources", "nginx_configs", "generated.conf"
    )
    with open(output_path, "w") as f:
        f.write("\n".join(blocks))
        f.write("\n")

    print(f"  nginx generated.conf generado")
    return output_path


def _server_block(inst_name, external_port, container_name):
    return f"""# Instance: {inst_name} (port {external_port})
server {{
    listen {external_port};
    server_name localhost;

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
