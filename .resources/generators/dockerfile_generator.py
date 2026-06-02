"""
Generates Dockerfiles for each unique Odoo version.
Concatenates the version-specific Dockerfile with the common Dockerfile.template.
"""

import os
import sys


def generate_dockerfiles(base_path, unique_versions):
    """
    Generate .resources/Dockerfile.{version} for each unique Odoo version.
    Returns a dict mapping version -> dockerfile relative path.
    """
    resources_dir = os.path.join(base_path, ".resources")
    dockerfiles_dir = os.path.join(resources_dir, "dockerfiles")
    template_path = os.path.join(resources_dir, "Dockerfile.template")

    if not os.path.exists(template_path):
        print("Error: Dockerfile.template no encontrado")
        sys.exit(1)

    with open(template_path, "r") as f:
        template_content = f.read()

    result = {}

    for version in unique_versions:
        version_dockerfile = os.path.join(
            dockerfiles_dir, f"{version}_Dockerfile"
        )
        if not os.path.exists(version_dockerfile):
            print(f"Error: Dockerfile para versión {version} no encontrado: {version_dockerfile}")
            sys.exit(1)

        with open(version_dockerfile, "r") as f:
            version_content = f.read()

        output_path = os.path.join(resources_dir, f"Dockerfile.{version}")
        with open(output_path, "w") as f:
            f.write(version_content)
            f.write("\n")
            f.write(template_content)
            f.write("\n")

        result[version] = f".resources/Dockerfile.{version}"
        print(f"  Dockerfile generado: {result[version]}")

    return result
