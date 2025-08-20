#!/bin/sh

# Mejorado: restaura una base de datos Odoo desde .sql, .sql.gz o .zip
# -b contenedor base de datos
# -o contenedor odoo
# -f archivo de backup (.sql, .sql.gz, .zip)
# -d nombre de base de datos

while getopts :b:o:f:d: flag
do
    case "${flag}" in
        b) database_container=${OPTARG};;
        o) odoo_container=${OPTARG};;
        f) file_compress=${OPTARG};;
        d) database_name=${OPTARG};;        
        :)                                    
            echo "Error: -${OPTARG} requires an argument."
            exit_abnormal
        ;;
        *)
            exit_abnormal
        ;;
    esac
done

unzip_file(){
    echo "Preparando backup... ${file_compress}"
    mkdir -p backup_tmp
    # Detecta el tipo de archivo y extrae según corresponda
    #!/bin/bash

    # Script para restaurar una base de datos Odoo desde archivos .sql, .zip (dump.sql + filestore), o .dump (pg_dump custom)
    # Uso: restore_db.sh -b <db_container> -d <db_name> -f <archivo> [-o <odoo_container>]
    # Ejemplo: ./restore_db.sh -b odoo-db -d example_bp_db -f /ruta/backup.dump

    while getopts :b:d:f:o:h flag
    do
        case "${flag}" in
            b) database_container=${OPTARG};;
            d) database_name=${OPTARG};;
            f) backup_file=${OPTARG};;
            o) odoo_container=${OPTARG};;
            h)
                usage
                exit 0
                ;;
            :)
                echo "Error: -${OPTARG} requiere un argumento."
                usage
                exit 1
                ;;
            *)
                usage
                exit 1
                ;;
        esac
    done

    usage() {
        echo "\nUso: $0 -b <db_container> -d <db_name> -f <archivo> [-o <odoo_container>]"
        echo "\nArgumentos:"
        echo "  -b    Nombre del contenedor Docker de Postgres"
        echo "  -d    Nombre de la base de datos a restaurar"
        echo "  -f    Ruta al archivo de backup (.sql, .zip, .dump)"
        echo "  -o    (Opcional) Contenedor de Odoo para restaurar filestore"
        echo "  -h    Mostrar esta ayuda"
        echo "\nEjemplo: $0 -b odoo-db -d example_bp_db -f /ruta/backup.dump"
    }

    if [ -z "$database_container" ] || [ -z "$database_name" ] || [ -z "$backup_file" ]; then
        echo "\nFaltan argumentos requeridos."
        usage
        exit 1
    fi

    create_database() {
        echo "\nCreando base de datos '${database_name}' en el contenedor '${database_container}'..."
        docker exec -i "$database_container" psql -U odoo postgres -c "DROP DATABASE IF EXISTS \"$database_name\";"
        docker exec -i "$database_container" psql -U odoo postgres -c "\
    CREATE DATABASE \"$database_name\" \
        WITH OWNER = odoo \
        TEMPLATE = template0 \
        ENCODING = 'UTF8' \
        LC_COLLATE = 'C' \
        LC_CTYPE = 'en_US.UTF-8' \
        LOCALE_PROVIDER = 'libc' \
        TABLESPACE = pg_default \
        CONNECTION LIMIT = -1 \
        IS_TEMPLATE = False;"
        echo "Base de datos creada."
    }

    restore_sql() {
        echo "\nRestaurando backup .sql en '${database_name}'..."
        cat "$backup_file" | docker exec -i "$database_container" psql -U odoo "$database_name"
        echo "Restauración completada."
    }

    restore_dump() {
        echo "\nRestaurando backup .dump en '${database_name}'..."
        cat "$backup_file" | docker exec -i "$database_container" pg_restore --verbose --clean --no-acl --no-owner -U odoo -d "$database_name"
        echo "Restauración completada."
    }

    restore_zip() {
        echo "\nDescomprimiendo backup zip..."
        mkdir -p backup_tmp
        unzip -o "$backup_file" -d backup_tmp
        if [ ! -f backup_tmp/dump.sql ]; then
            echo "No se encontró dump.sql en el zip. Abortando."
            rm -rf backup_tmp
            exit 1
        fi
        echo "\nRestaurando dump.sql en '${database_name}'..."
        cat backup_tmp/dump.sql | docker exec -i "$database_container" psql -U odoo "$database_name"
        if [ -n "$odoo_container" ] && [ -d backup_tmp/filestore ]; then
            echo "\nRestaurando filestore en contenedor Odoo..."
            docker exec -u odoo -i "$odoo_container" mkdir -p /var/lib/odoo/filestore
            docker exec -u odoo -i "$odoo_container" mkdir -p /var/lib/odoo/filestore/"$database_name"
            docker cp backup_tmp/filestore/. "$odoo_container":/var/lib/odoo/filestore/"$database_name"
            echo "Filestore restaurado."
        fi
        rm -rf backup_tmp
        echo "Backup zip restaurado."
    }

    main() {
        create_database
        ext="${backup_file##*.}"
        case "$ext" in
            sql)
                restore_sql
                ;;
            dump|pg_dump)
                restore_dump
                ;;
            zip)
                restore_zip
                ;;
            *)
                echo "\nTipo de archivo no soportado: $ext"
                exit 1
                ;;
        esac
        echo "\nRecuerda actualizar los módulos de Odoo si es necesario:"
        echo "  sudo docker exec -it <odoo_container> odoo -d $database_name -u base --stop-after-init"
        echo "\nRestauración finalizada."
    }

    main
    else
        echo "No se encontró filestore. Saltando."
    fi
}

clear(){
    echo "Limpiando backup temporal..."
    rm -rf backup_tmp
    echo "Backup temporal eliminado."
}

usage() {
    echo "Uso: $0 [ -b DATABASE_CONTAINER ] [ -o ODOO_CONTAINER ] [-f FILE_BACKUP] [-d DATABASE_NAME]" 1>&2 
}
exit_abnormal() {
    usage
    exit 1
}

main(){
    unzip_file
    load_database
    load_filestore
    clear
}

main