#!/bin/sh

# Script para crear un backup de una base de datos Odoo y su filestore
# Uso: ./backup_db.sh -b <db_container> -d <db_name> -o <output_path> [-f <filestore_path_en_contenedor>]

while getopts :b:d:o:f: flag; do
  case "${flag}" in
    b) db_container=${OPTARG};;
    d) db_name=${OPTARG};;
    o) output_path=${OPTARG};;
    f) filestore_path=${OPTARG};;
    *) echo "Uso: $0 -b <db_container> -d <db_name> -o <output_path> [-f <filestore_path_en_contenedor>]"; exit 1;;
  esac
done

if [ -z "$db_container" ] || [ -z "$db_name" ] || [ -z "$output_path" ]; then
  echo "Faltan argumentos."
  echo "Uso: $0 -b <db_container> -d <db_name> -o <output_path> [-f <filestore_path_en_contenedor>]"
  exit 1
fi

set -e

# Backup de la base de datos
backup_file="${db_name}_$(date +%Y-%m-%d_%H-%M-%S).sql.gz"
echo "Generando backup de $db_name en $db_container..."
sudo docker exec $db_container pg_dump -U odoo $db_name > /tmp/${db_name}.sql
sudo docker exec $db_container gzip /tmp/${db_name}.sql
sudo docker cp $db_container:/tmp/${db_name}.sql.gz $output_path/$backup_file
sudo docker exec $db_container rm /tmp/${db_name}.sql.gz
echo "Backup de base de datos listo en $output_path/$backup_file"

# Backup del filestore (opcional)
if [ ! -z "$filestore_path" ]; then
  echo "Copiando filestore desde el contenedor..."
  filestore_dest="$output_path/filestore_${db_name}_$(date +%Y-%m-%d_%H-%M-%S).tar.gz"
  sudo docker exec $db_container tar czf /tmp/filestore_${db_name}.tar.gz -C "$filestore_path" .
  sudo docker cp $db_container:/tmp/filestore_${db_name}.tar.gz $filestore_dest
  sudo docker exec $db_container rm /tmp/filestore_${db_name}.tar.gz
  echo "Filestore guardado en $filestore_dest"
else
  echo "No se especificó ruta de filestore, solo se respaldó la base de datos."
fi
