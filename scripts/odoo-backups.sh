#!/bin/sh
servers_file="servers.json" # Archivo con lista de servidor con la informacion para coneccion ssh, docker ...
config_file="config.json" # Archivo con valores de configuracion general. Algunos valores pueden ser sobreescritos en $servers_file

# Leer variables por defecto de $config_file
if [ -n "$config_file" ] && [ -f "$config_file" ]
then
    default_values=$(jq . $config_file)    
else
    echo "Archivo de configuración \"$config_file\" no encontrado o sin acceso"
    exit 1
fi

#Ejecución principal de los backups
if [ -n "$servers_file" ] && [ -f "$servers_file" ]
then
    servers=$(jq . $servers_file) # cargar info de los servidores

    servers_exec=$(echo "$default_values" | jq -r ".servers_exec") # keys de los servidores en el archivo $servers_file separada por espacio, o all para todos los servidores
    
    #obtener lista de servidores para genera backups
    if [ -z "$servers_exec" ] || [ "$servers_exec" = "null" ] || [ "$servers_exec" = "all" ]
    then
        keys=$(echo "$servers" | jq -r "keys[]")
    else
        keys=$servers_exec
    fi

    #Inici a el ciclo para generar backucks de cada servidor
    for key in $keys
    do
        server=$(echo "$servers" | jq -r ".$key") #obtener info del servidor actual
        
        if [ -n "$server" ] && [ "$server" != "null" ]
        then
            echo "Procesando servidor: $key"
            host=$(echo "$server" | jq -r ".host") #host o ip del servidor
            ssh=$(echo "$server" | jq ".ssh") # si connection_type es "ssh" tedra la info para hacer la conección via ssh
            db=$(echo "$server" | jq ".postgres") # Info para connectar con postgres
            file_date=$(TZ=America/Caracas date +%Y-%m-%d_%H_%M) #fecha y hora que se usara para nombra archivos
            file_db_ext="" #Extensión para el archivo de backup de bd
            
            #Variables conectar con postgres
            if [ -n "$db" ] && [ "$db" != "null" ] 
            then
                db_user=$(echo "$db" | jq -r ".user")
                db_name=$(echo "$db" | jq -r ".db_name")
                db_use_pass=$(echo "$db" | jq -r ".use_pass") # Indica si se necesita password o no
                db_password=$(echo "$db" | jq -r ".password")
                db_format=$(echo "$db" | jq -r ".format") # Formato con que se creara el backup, sera solo una letra: p: plain, c: custom, d: directory, t: tar
                db_host=$(echo "$db" | jq -r ".host")
                db_port=$(echo "$db" | jq -r ".port")
                tmp_dir="tmp/${db_name}_$file_date"

                # echo "db_use_password: $db_use_pass"
                # echo "db_password: $db_password"
                
                sql="pg_dump -U $db_user"

                if [ -n "$db_format" ] && [ "$db_format" != "null" ]
                then
                    sql=$sql" -F $db_format"
                else
                    db_format=$(echo "$default_values" | jq -r ".postgres.format") #Asignar valor por defecto
                    if [ -n "$db_format" ] && [ "$db_format" != "null" ]
                    then
                        sql=$sql" -F $db_format"
                    fi                 
                fi
                
                #definir extensión para archivo del backup de db
                if [ -z "$db_format" ] || [ "$db_format" = "null" ] || [ "$db_format" = "p" ]
                then
                    file_db_ext=".sql"
                elif [ "$db_format" = "t" ] 
                then
                    file_db_ext=".tar"
                fi
                
                if [ -n "$db_host" ] && [ "$db_host" != "null" ]
                then
                    sql=$sql" -h $db_host " 
                fi
                
                if [ -n "$db_port" ] && [ "$db_port" != "null" ]
                then
                    sql=$sql" -p $db_port " 
                fi

                sql="$sql $db_name"
                # echo "sql -> $sql"
                # if [ -n "$db_use_pass" ] && [ "$db_use_pass" != "null" ] && [ "$db_use_pass" = "true" ]
                # then
                #     $ = ""
                # fi
            fi

            odoo_type=$(echo "$server" | jq -r ".odoo_type") # tipo de instalacion de odoo puede ser "docker" o "local" si esta instalado directamente en el servidor
            containers=$(echo "$server" | jq -r ".containers") # si odoo_type es "docker" tendra Info de los contenedores de odoo sino sera vacia o nulo
            target_path=$(echo "$server" | jq -r ".target_path") # directorio donde se guardaran los bakups 
            project_path=$(echo "$server" | jq -r ".project_path") # directorio donde esta montado el proyecto
            
            #tipo de instalacion de odoo es docker, 
            if [ "$odoo_type" = "docker" ] && [ -n "$containers" ] && [ "$containers" != "null" ]
                then
                    # echo "project_path: $project_path"

                    #Variables para Respaldo DB
                    db_project_path=$(echo "$containers" | jq -r ".db.project_path") #Directorio del proyecto de base de datos
                    
                    #Validar existe db_project_path para el servidor sino asignar project_path
                    if [ -z "$db_project_path" ] || [ "$db_project_path" = "null" ]
                    then
                        db_project_path=$project_path
                    fi
                    # echo "db project_path: $db_project_path"

                    db_target_cont_path=$(echo "$containers" | jq -r ".db.target_cont_path")
                    db_volume_path=$(echo "$containers" | jq -r ".db.volume_path")
                    db_service_name=$(echo "$containers" | jq -r ".db.service_name")
                    db_container_name=$(echo "$containers" | jq -r ".db.container_name")

                    # echo "db_target_cont_path: $db_target_cont_path"
                    # echo "db_volume_path: $db_volume_path"
                    # echo "db_service_name: $db_service_name"
                    # echo "db_container_name: $db_container_name"
                    
                    #actualizar 
                    sql="$sql -f $db_target_cont_path/${db_name}_$file_date$file_db_ext"
                    # echo "sql -> $sql"

                    #Variables para Respaldo Filestore
                    odoo_project_path=$(echo "$containers" | jq -r ".odoo.project_path") #Directorio del proyecto odoo
                  
                    #Validar existe odoo_project_path para el servidor sino asignar project_path
                    if [ -z "$odoo_project_path" ] || [ "$odoo_project_path" = "null" ]
                    then
                        odoo_project_path=$project_path
                    fi
                    # echo "odoo project_path: $odoo_project_path"

                    odoo_source_cont_path=$(echo "$containers" | jq -r ".odoo.source_cont_path")
                    odoo_volume_path=$(echo "$containers" | jq -r ".odoo.volume_path")
                    odoo_service_name=$(echo "$containers" | jq -r ".odoo.service_name")
                    odoo_container_name=$(echo "$containers" | jq -r ".odoo.container_name")

                    # echo "odoo_source_cont_path: $odoo_source_cont_path"
                    # echo "odoo_volume_path: $odoo_volume_path"
                    # echo "odoo_service_name: $odoo_service_name"
                    # echo "odoo_container_name: $odoo_container_name"
            fi 
            
            conn_type=$(echo "$server" | jq -r ".connection_type") # tipo de conección puede ser "ssh" si es un servidor remoto o "local" si es el servidor donde corre el script

            #Validar existe connection_type para el servidor sino asignar valor por defecto
            if [ -z "$conn_type" ] || [ "$conn_type" = "null" ] 
            then 
                conn_type=$(echo "$default_values" | jq -r ".connection_type")
            fi
            
            # echo "connection_type: $conn_type"
            
            # tipo de connecions ssh
            if [ "$conn_type" = "ssh" ] && [ -n "$ssh" ] && [ "$ssh" != "null" ]
             then
                ssh_user=$(echo "$ssh" | jq -r ".user") # usuario para conectar por ssh
                ssh_port=$(echo "$ssh" | jq -r ".port") # puerto para conectar pos ssh

                #Validar existe ssh.port para el servidor sino asignar valor por defecto
                if [ -z "$ssh_port" ] || [ "$ssh_port" = "null" ] 
                then 
                    ssh_port=$(echo "$default_values" | jq -r ".ssh.port")
                fi

                ssh_key_file=$(echo "$ssh" | jq -r ".key_file") # ruta del archivo con la llave ssh 

                #Validar existe key_file para el servidor sino asignar valor por defecto
                if [ -z "$ssh_key_file" ] || [ "$ssh_key_file" = "null" ] 
                then 
                    ssh_key_file=$(echo "$default_values" | jq -r ".ssh.key_file")
                fi
                
                #tipo de instalacion de odoo es docker
                if [ "$odoo_type" = "docker" ] && [ -n "$containers" ] && [ "$containers" != "null" ]
                then
                    echo "Tipo de instalacion docker"
                    echo "Conectando por ssh al host $host"
                    ssh -i "$ssh_key_file" -p "$ssh_port" -T "$ssh_user"@"$host" << EOT
                
                    #Respaldo DB
                    echo "Generar backup de base de datos $db_name"
                    if [ -n "$db_project_path" ] && [ "$db_project_path" != "null" ] && [ -d "$db_project_path" ]
                    then
                        cd $db_project_path
                        echo "Cambiado a directorio: \${PWD}"
                    else
                        echo "Directorio $db_project_path no encontrado"
                        exit
                    fi
                                        
                    # if [ -n "$db_service_name" ] && [ "$db_service_name" != "null" ]
                    # then
                    #     echo "Asegurar que exista directorio destino contenedor: $db_target_cont_path"
                    #     docker-compose exec -T $db_service_name mkdir -p $db_target_cont_path
                    #     echo "Ejecutando pg_dump con docker-compose"

                    #     if [ -n "$db_use_pass" ] && [ "$db_use_pass" != "null" ] && [ "$db_use_pass" = true ] 
                    #     then
                    #         echo "pgdump usando password"
                    #         docker-compose exec -T $db_service_name bash -c "export PGPASSWORD='$db_password' && $sql && unset PGPASSWORD"
                    #     else
                    #         echo "pgdump usando sin password"
                    #         docker-compose exec -T $db_service_name $sql
                    #     fi

                    #     echo "Asegurar que exista directorio destino: $target_path/tmp"
                    #     mkdir -p $target_path/$tmp_dir
                    #     if [ -n "$db_volume_path" ] && [ "$db_volume_path" != "null" ] && [ -d "$db_volume_path" ]
                    #     then
                    #         echo "copiando backup desde volumen $db_volume_path en $target_path/$tmp_dir"
                    #         cp $db_volume_path/${db_name}_$file_date$file_db_ext $target_path/$tmp_dir
                    #         echo  "Eliminar backup del contendor en $db_target_cont_path/${db_name}_$file_date$file_db_ext"
                    #         docker-compose exec -T $db_service_name rm $db_target_cont_path/${db_name}_$file_date$file_db_ext
                    #     else
                    #         echo "copiando backup desde contenedor $db_volume_path en $target_path/$tmp_dir"
                    #         docker cp $db_container_name:$db_target_cont_path/${db_name}_$file_date$file_db_ext $target_path/$tmp_dir
                    #         echo  "Eliminar backup del contendor en $db_target_cont_path/${db_name}_$file_date$file_db_ext"
                    #         docker-compose exec -T $db_service_name rm $db_target_cont_path/${db_name}_$file_date$file_db_ext
                    #     fi
                    # elif [ -n "$db_container_name" ] && [ "$db_container_name" != "null" ]
                    # then
                    #     echo "Asegurar que exista directorio destino contenedor: $db_target_cont_path"
                    #     docker exec -i $db_container_name mkdir -p $db_target_cont_path
                        
                    #     echo "Ejecutando pg_dump con docker exec"
                    #     if [ -n "$db_use_pass" ] && [ "$db_use_pass" != "null" ] && [ "$db_use_pass" = true ] 
                    #     then
                    #         echo "pgdump usando password"
                    #         docker exec -i $db_container_name bash -c "export PGPASSWORD='$db_password' && $sql && unset PGPASSWORD"
                    #     else
                    #         echo "pgdump sin usar password"
                    #         docker exec -i $db_container_name $sql   
                    #     fi

                    #     if [ -n "$db_volume_path" ] && [ "$db_volume_path" != "null" ] && [ -d "$db_volume_path" ]
                    #     then
                    #     echo 
                    #         echo "copiando backup desde volumen $db_volume_path en $target_path/$tmp_dir"
                    #         cp $db_volume_path/${db_name}_$file_date$file_db_ext $target_path/$tmp_dir
                    #         echo  "Eliminar backup del contendor en $db_target_cont_path/${db_name}_$file_date$file_db_ext"
                    #         docker exec -i $db_container_name rm $db_target_cont_path/${db_name}_$file_date$file_db_ext
                    #     else
                    #         echo "copiando backup desde contenedor $db_target_cont_path en $target_path/$tmp_dir"
                    #         docker cp $db_container_name:$db_target_cont_path/${db_name}_$file_date$file_db_ext $target_path/$tmp_dir
                    #         echo  "Eliminar backup del contendor en $db_target_cont_path/${db_name}_$file_date$file_db_ext"
                    #         docker exec -i $db_container_name rm $db_target_cont_path/${db_name}_$file_date$file_db_ext
                    #     fi
                    # else
                    #     echo "Es requerido el nombre del servicio y/o nombre del contenedor para genera backup de db"
                    #     exit
                    # fi
                    
                    #Respaldo Filestore

                    echo "Generar backup de filestore $db_name"
                    
                    if [ -n "$odoo_project_path" ] && [ "$odoo_project_path" != "null" ] && [ -d "$odoo_project_path" ]
                    then
                        cd $odoo_project_path
                        echo "Cambiado a directorio: \${PWD}"
                    else
                        echo "Directorio $odoo_project_path no encontrado"
                        exit
                    fi

                    echo "Asegurar que exista directorio destino: $target_path/$tmp_dir"
                    mkdir -p $target_path/$tmp_dir
                    if [ -n "$odoo_volume_path" ] && [ "$odoo_volume_path" != "null" ] && [ -d "$odoo_volume_path" ]
                    then
                        echo "copiando directorio filestore desde volumen $odoo_volume_path/$db_name en $target_path/$tmp_dir"
                        cp -r $odoo_volume_path/${db_name} $target_path/$tmp_dir
                    elif [ -n "$db_container_name" ] && [ "$db_container_name" != "null" ]
                    then
                        echo "copiando directorio filestore desde contenedor $odoo_source_cont_path/$db_name en $target_path/$tmp_dir"
                        docker cp $odoo_container_name:$odoo_source_cont_path/$db_name $target_path/$tmp_dir/
                    else
                        echo "Es requerido el directorio del volumen o el nombre del contenedor para respaldar filestore"
                        exit
                    fi
                    
                    exit
EOT
                
                    # ssh -i "$ssh_key_file" -p "$ssh_port" "$ssh_user"@"$host" "whoami; pwd; ls; exit"
                fi
            elif [ "$conn_type" = "local" ] && [ -n "$local" ] && [ "$local" != "null" ] 
            then
                echo "conn_type local"
            fi
           
        else
            echo "Server \"$key\" no encontrado en $servers_file"
        fi  
    done
else
    echo "Archivo de servidores \"$servers_file\" no encontrado o sin acceso"
    exit 1
fi
