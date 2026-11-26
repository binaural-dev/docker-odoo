# Cobertura de código en staging y release, sin gastar tokens

Para medir la cobertura de los módulos personalizados de un cliente **no hace falta que Claude corra las pruebas ni que vigile el proceso**. docker-odoo ya trae lo necesario: `./odoo sync` cambia los repos de rama y `./odoo coverage` corre las pruebas y genera el reporte.

## 1. El comando

Ábrelo en la raíz de docker-odoo. Cambia solo los nombres dentro de `REPOS=(...)`: son las carpetas de `src/custom`.

```bash
REPOS=(cliente-a cliente-b)
for RAMA in staging release; do
  for R in "${REPOS[@]}"; do ./odoo sync "$R" "$RAMA"; done
  ./odoo coverage "${REPOS[@]}" --out "coverage_data/cobertura-$RAMA-$(date +%Y%m%d).csv"
done
```

Corre solo, de principio a fin. Primero sincroniza todos los repos con `staging` y mide la cobertura; después hace lo mismo con `release`.

## 2. El resultado

- Dos CSV en `coverage_data/`: `cobertura-staging-AAAAMMDD.csv` y `cobertura-release-AAAAMMDD.csv`.
- En la terminal, una tabla con el porcentaje por proyecto. El mínimo esperado es 70 %; se cambia con `--threshold=60`.

## 3. Antes de correrlo

- **Cambios locales:** `./odoo sync` guarda con `git stash` los cambios sin commitear de cada repo antes de cambiar de rama. Se recuperan con `git stash pop` dentro del repo.
- **Solo se miden módulos con `tests/`.** Para ver qué clientes tienen pruebas: `./odoo coverage-status --only-with-tests`.
- **Para revisar sin ejecutar:** agrega `--dry-run` al `./odoo coverage` y muestra el plan sin tocar nada.

## 4. Errores comunes

| Si haces esto | Pasa esto | Mejor así |
|---|---|---|
| `REPOS="cliente-a cliente-b"` | En zsh (la terminal por defecto en Mac) no se separa: el ciclo corre una sola vez con "cliente-a cliente-b" | `REPOS=(cliente-a cliente-b)` |
| Agregar `exit` o `set -e` al bloque | Al primer error se cierra la terminal | Dejar el bloque como está |
| Correrlo fuera de la raíz de docker-odoo | `./odoo` no existe | `cd` a la carpeta de docker-odoo primero |

## 5. Si igual quieres pedírselo a Claude

Este prompt hace que Claude **solo arme el comando**, sin ejecutar ni leer nada, así que gasta muy pocos tokens. Reemplaza los repos y pégalo:

```text
Ármame el comando para medir cobertura en docker-odoo. NO ejecutes nada, NO leas
archivos y NO monitorees procesos: responde solo con un bloque de código y, como
mucho, dos líneas de aviso.

Repos (carpetas de src/custom): <cliente-a cliente-b>
Ramas: staging y release, en ese orden.

Usa exactamente esta forma:

REPOS=(<repos separados por espacio>)
for RAMA in staging release; do
  for R in "${REPOS[@]}"; do ./odoo sync "$R" "$RAMA"; done
  ./odoo coverage "${REPOS[@]}" --out "coverage_data/cobertura-$RAMA-$(date +%Y%m%d).csv"
done

Reglas: usa un array REPOS=(...) con "${REPOS[@]}" (en zsh un string con espacios
no se separa); no agregues exit ni set -e (cierran la terminal). Avisos permitidos:
que sync hace stash de los cambios locales y que solo se miden módulos con tests/.
```

Cuando el comando esté corriendo, no hace falta volver a Claude: el resultado queda en los CSV.
