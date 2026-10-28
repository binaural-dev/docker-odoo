# AI_LOG — payment_request (Ejercicio 4)

## Herramientas
- Claude Code (app de escritorio), modelo Claude Opus 5.5.

## Prompts clave
1. «Arranca el ejercicio 4-A (payment_request) en una rama nueva.»
   - Diseñó el modelo con las reglas en `write()` (campos bloqueados, transiciones y grupo por estado
     destino) para que valgan también ante un `write` por RPC, no solo desde el botón. Agregó una regla que no
     estaba en el pedido: nadie aprueba su propia solicitud. Quedó documentada como supuesto.
2. Pruebas de «lo que no se debe poder hacer»: aprobar por método y por `write`, editar una enviada, montos
   inválidos, transiciones inválidas y botones por grupo (inspeccionando la vista que recibe cada usuario).

## Lo que la IA hizo mal
- **Referencia circular de grupos:** el primer borrador hacía que *Solicitante* implicara `base.group_user`
  y, a la vez, que `base.group_user` implicara *Solicitante*. Odoo rechaza esa recursión. Se corrigió antes
  de instalar, al releer el XML.
- **Una línea sin sentido en una prueba** (`fields.Date.today().year[:0]`, que falla con un entero). Se vio al
  revisar el archivo antes de correrlo.
- **Prueba del chatter mal planteada, dos veces:** primero asumió que el seguimiento se publica con
  `flush_all()` (se publica en el *precommit*), y luego leyó `mail.tracking.value` con el empleado, que no
  tiene permiso de lectura. Se detectó al correr las pruebas.

## Lo que escribiste tú sin IA
- (Completar por Candido: qué partes decidiste o escribiste por tu cuenta y por qué.)
