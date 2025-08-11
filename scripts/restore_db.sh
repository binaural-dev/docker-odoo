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
    case "${file_compress}" in
        *.zip)
            unzip "${file_compress}" -d backup_tmp
            # Busca dump.sql dentro del zip
            if [ -f backup_tmp/dump.sql ]; then
                SQLFILE="dump.sql"
            else
                SQLFILE=$(ls backup_tmp/*.sql 2>/dev/null | head -n1 | xargs -n1 basename)
                # Si no hay .sql, busca .dump
                if [ -z "$SQLFILE" ]; then
                    SQLFILE=$(ls backup_tmp/*.dump 2>/dev/null | head -n1 | xargs -n1 basename)
                fi
            fi
            ;;
        *.gz)
            cp "${file_compress}" backup_tmp/
            gunzip -c "${file_compress}" > backup_tmp/dump.sql
            SQLFILE="dump.sql"
            ;;
        *.sql)
            cp "${file_compress}" backup_tmp/dump.sql
            SQLFILE="dump.sql"
            ;;
        *.dump)
            cp "${file_compress}" backup_tmp/dump.dump
            SQLFILE="dump.dump"
            ;;
        *)
            echo "Tipo de archivo de backup no soportado: ${file_compress}"
            exit 1
            ;;
    esac
    echo "Backup preparado: backup_tmp/${SQLFILE}"
}

load_database(){  
    echo "Verificando si la base de datos '${database_name}' existe..."
    cd backup_tmp
    exists=$(docker exec -i ${database_container} psql -U odoo -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='${database_name}';")
    if [ "$exists" = "1" ]; then
        echo "La base de datos '${database_name}' ya existe. Terminando conexiones y eliminando para restaurar..."
        docker exec -i ${database_container} psql -U odoo -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${database_name}' AND pid <> pg_backend_pid();"
        docker exec -i ${database_container} psql -U odoo -d postgres -c "DROP DATABASE IF EXISTS ${database_name};"
    fi
    echo "Creando base de datos '${database_name}'..."
    docker exec -i ${database_container} psql -U odoo -d postgres -c "CREATE DATABASE ${database_name};"
    echo "Restaurando backup en '${database_name}'..."
    if [ "${SQLFILE##*.}" = "dump" ]; then
        docker cp "${SQLFILE}" ${database_container}:/tmp/${SQLFILE}
        docker exec -i ${database_container} pg_restore -U odoo -d ${database_name} /tmp/${SQLFILE}
        docker exec -i ${database_container} rm /tmp/${SQLFILE}
    else
        cat "${SQLFILE}" | docker exec -i ${database_container} psql -U odoo ${database_name}
    fi
    echo "Base de datos creada y restaurada."
    cd ..
}

load_filestore(){
    if [ -d backup_tmp/filestore ]; then
        echo "Copiando filestore..."
        # Contar archivos en el filestore
        file_count=$(find backup_tmp/filestore -type f | wc -l)
        echo "Cantidad de archivos en filestore: $file_count"
        # Consultar cantidad de adjuntos en la base de datos restaurada
        attachment_count=$(docker exec -i ${database_container} psql -U odoo -d ${database_name} -t -c "SELECT count(*) FROM ir_attachment;" | grep -Eo '^[ 0-9]+$' | tr -d ' ')
        echo "Cantidad de registros en ir_attachment: $attachment_count"
        echo "ADVERTENCIA: Si la cantidad de archivos y registros difiere mucho, el filestore podría estar incompleto. No se puede verificar integridad total."
        docker exec -u odoo -i ${odoo_container} mkdir -p /var/lib/odoo/filestore/${database_name}
        docker cp backup_tmp/filestore/. ${odoo_container}:/var/lib/odoo/filestore/${database_name}
        echo "Filestore copiado."
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