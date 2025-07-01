#!/bin/sh

#-b contenedor base de datos
#-o contenedor odoo
#-f archivo comprimido

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
    echo "Iniciando unzip... ${file_compress}"
    mkdir backup_tmp
    unzip ${file_compress} -d backup_tmp
    echo "Unzip completado."
}

load_database(){  
    echo "creando y cargando base de datos... ${database_name}"  
    cd backup_tmp
    docker exec -i ${database_container} psql -U odoo postgres -c 'drop database if exists '${database_name};''
    docker exec -i ${database_container} psql -U odoo postgres -c 'create database '${database_name};''
    cat dump.sql | docker exec -i ${database_container} psql -U odoo ${database_name}
    echo "base de datos creada y cargada."
}

load_filestore(){
    echo "copiando filestore (si existe)..."
    docker exec -u odoo -i ${odoo_container} mkdir /var/lib/odoo/filestore
    docker exec -u odoo -i ${odoo_container} mkdir /var/lib/odoo/filestore/${database_name}
    pwd
    docker cp filestore/. ${odoo_container}:/var/lib/odoo/filestore/${database_name}
    echo "filestore copiado (si habia filestore)."
}

clear(){
    echo "limpiando backup..."
    cd ..
    rm -rf backup_tmp
    echo "backup limpiado."
}

usage() {                                 # Function: Print a help message.
  echo "Uso: $0 [ -b DATABASE_CONTAINER ] [ -o ODOO_CONTAINER ] [-f FILE_ZIP] [-d DATABASE_NAME]" 1>&2 
}
exit_abnormal() {                         # Function: Exit with error.
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
