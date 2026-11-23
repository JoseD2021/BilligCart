# Pagos con Stripe

El modulo implementa Checkout, confirmaciones firmadas, solicitudes duraderas y eventos.
La integracion esta habilitada exclusivamente en Stripe TEST: no mueve dinero real.
Lee el total del pedido del usuario en Supabase, en COP, para probar el pago completo.
Como el carrito todavia utiliza precios de referencia, no se admiten claves live.
Los eventos de pago exitoso se guardan en la tabla Pagos de Supabase. SQLite conserva
el registro tecnico y los mensajes pendientes; el estado de reparto de Pedidos no cambia.
El esquema de Pagos esta versionado en migrations/004_create_pagos.sql.

## Flujo

1. El usuario solicita pagar un pedido: `POST /api/v1/pagos`, con token de sesion,
   `Idempotency-Key` y `{ "order_id": "UUID" }`. El cuerpo no admite importes.
2. `TestOrderQuotes` consulta el pedido del usuario en Supabase, verifica su propietario y
   captura su total/version como cotizacion de prueba durante una hora. Convierte COP a
   unidades menores con Decimal: 15000 COP -> 1500000. Nunca recibe el importe del cliente.
   `PAYMENTS_SANDBOX_FIXTURES=true` habilita esta ruta; false mantiene el cobro bloqueado.
3. Se guardan el intento y `payments.requested.v1` juntos en un registro tecnico SQLite.
   La API responde `202 queued`; eso significa solicitud recibida, NO pago exitoso.
4. El worker publica la outbox en RabbitMQ con confirmaciones del broker. Las colas son
   duraderas, los mensajes persistentes y los reintentos diferidos (5, 30 y 300 segundos).
   Stripe temporalmente caido conserva la misma solicitud y la misma clave de idempotencia.
   RabbitMQ caido conserva los mensajes en la outbox para enviarlos al recuperarse.
5. El worker crea una sesion de Stripe Checkout. El cliente consulta
   `GET /api/v1/pagos/pedido/{order_id}` y abre `checkout_url`. Las tarjetas se introducen
   en Stripe; BilligCart no recibe ni guarda sus datos.
   El panel muestra el importe del intento y los campos de configuracion que faltan.
   `GET /api/v1/pagos/configuracion`, autenticado, muestra estado TEST sin exponer secretos.
   Al terminar o cancelar, Stripe devuelve al frontend con el UUID del pedido. La app
   recupera el pedido en el paso Pago del carrito y consulta el backend; los parametros
   de retorno no confirman ningun pago. Tras la confirmacion se permite pasar a Envio.
6. Stripe llama a `POST /api/v1/pagos/webhook/stripe`. Se comprueban firma HMAC, antiguedad,
   modo test/live, pedido interno, sesion, moneda e importe. La redireccion del navegador
   nunca marca el pedido como pagado. `completed` sin `paid` queda en `processing`.
7. El webhook guarda estado, deduplicacion y `payments.succeeded.v1` atomicamente.
   El cliente obtiene `succeeded` y muestra el mensaje de pago exitoso.
8. El servicio general `event_worker` consume `PaymentSucceeded` y ejecuta su handler.
   `SupabasePaymentProjection` comprueba el evento contra la outbox y el pago confirmado,
   e inserta en `public."Pagos"` con `payment_id` como clave de deduplicacion. Una entrega
   repetida no sobrescribe la fila. Se verifica la escritura y luego se guarda el recibo
   tecnico local. Ante un fallo de Supabase el mensaje se reintenta, sin volver a cobrar.
   `LocalPaymentProjection` se conserva para pruebas aisladas. En produccion payment_worker
   solo procesa solicitudes hacia Stripe; no consume ni persiste PaymentSucceeded.
9. Al arrancar, el worker vuelve a publicar los exitos confirmados que no tienen recibo
   de aplicacion en Supabase. Esto recupera los pagos anteriores a la creacion de Pagos,
   conservando el mismo evento y fecha de confirmacion y sin llamar a Stripe para cobrar.

La distribucion de mensajes la hace RabbitMQ. event_worker registra los handlers de IA,
GPS y pagos. Observa PaymentRequested sin ejecutar el cobro, y aplica PaymentSucceeded a
Supabase. payment_worker publica la outbox y ejecuta Stripe. Los eventos se generan en el
backend: event_worker es su consumidor general, no un paso obligatorio para publicarlos.

## Fallos y reintentos

- Tarjeta rechazada: el usuario puede corregirla en la misma sesion de Checkout.
- Cancelar/volver desde Stripe no demuestra que haya fallado el pago: se conserva la sesion.
- Sesion vencida o fallo terminal: se permite otro intento con otra `Idempotency-Key`,
  previa conciliacion del intento anterior con Stripe. Si Stripe revela que ya estaba
  pagado, se confirma ese pago y no se crea otra sesion. Si aun esta abierto/pendiente,
  se espera su resolucion. La comprobacion conservadora exige sesion expirada y no pagada.
- Repetir la misma clave HTTP devuelve el mismo intento; distintas claves concurrentes
  tampoco crean otro intento activo para el mismo pedido. Un pedido pagado no se cobra otra vez.
- Timeout o respuesta incierta: se reintenta la misma operacion, sin cambiar importe ni clave.
- Mas de 23 horas desde el primer envio incierto: pasa a `review_required`. Stripe puede
  eliminar claves tras 24 horas; se exige conciliacion manual antes de arriesgar otro cobro.
- Error permanente de configuracion/API: requiere revision. No se genera otro cobro automatico.
- Mensajes invalidos: cola `.dead`; errores transitorios: colas `.retry.*`. Los originales
  se confirman solo despues de confirmar la entrega al siguiente destino.
- Eventos repetidos o desordenados: el exito es definitivo; un fallo tardio no lo revierte.

## Persistencia y alcance

Para seguir el flujo en tiempo real:

```bash
docker compose logs -f --tail=100 backend event_worker payment_worker
```

Los registros INFO incluyen payment_id y event_id para correlacionar los pasos:
`payment_request_recorded`, `stripe_webhook_applied`, `payment_event_recorded`,
`payment_event_published`, `payment_event_received`, `payment_projection_applied`
y `payment_success_consumed`. Un evento repetido muestra `payment_projection_duplicate`.
`payment_projection_applied target=supabase.Pagos` identifica la escritura confirmada
en Supabase. `payment_projection_duplicate` indica que la fila ya estaba guardada.
Estos mensajes aparecen con prefijo event_worker, junto a event_received, payment_success_received,
payment_success_consumed y event_processed. La generacion payment_event_recorded aparece
en backend y la publicacion payment_event_published en payment_worker.
El arranque muestra `payment_projection_backfill_queued` y la cantidad a recuperar.
Los pagos anteriores a estas trazas conservan sus datos aunque no tengan logs historicos.

`PAYMENTS_JOURNAL_PATH` es un registro tecnico del modulo de pagos, separado de Supabase.
Los datos de negocio confirmados quedan en Pagos: usuario, pedido, importe en unidades
menores, moneda, sesion Stripe, evento, status=succeeded, modo TEST y fecha de confirmacion.
La columna created_at indica cuando se inserto en Supabase; confirmed_at conserva la fecha
del evento original. Las claves unicas de pago, evento y sesion evitan duplicados.
La tabla Pedidos mantiene su estado de entrega; no se lo reemplaza por un estado de pago.
En Compose, API y worker comparten el volumen `payment-journal`; RabbitMQ usa `rabbitmq-data`.
Conservar ambos volumenes. `docker compose down -v` elimina esos datos.
El SQLite compartido es una solucion de un solo host; para replicas en multiples hosts
se debe sustituir por almacenamiento transaccional compartido y mantener la outbox/inbox.
No se almacenan tarjetas. El modulo no implementa reembolsos, disputas ni entrega/reparto.

## Configuracion y prueba manual en Stripe TEST

1. En el sandbox de tu cuenta Stripe, copia la clave secreta de API en
   `STRIPE_SECRET_KEY` dentro de `backend/.env`. Debe empezar por `sk_test_`.
   No es la clave publica `pk_test_`. No se coloca en frontend/.env ni en Git.
   Supabase debe tener la tabla Pagos con el esquema de migrations/004_create_pagos.sql,
   y SUPABASE_KEY debe ser una clave de servidor con permiso para insertar en esa tabla.
2. Activa `PAYMENTS_SANDBOX_FIXTURES=true` y deja `PAYMENTS_TEST_CURRENCY=cop`.
   Se usa el total GUARDADO del pedido, no un importe fijo. Es una simulacion financiera
   en Stripe TEST; los precios de referencia del carrito no habilitan cobros reales.
3. Configura `STRIPE_SUCCESS_URL` y `STRIPE_CANCEL_URL` con la URL accesible del frontend,
   por ejemplo `http://localhost:8081/`. El servidor agrega el pedido y el tipo de retorno.
4. Inicia Stripe CLI:

   ```bash
   stripe login
   stripe listen --events checkout.session.completed,checkout.session.expired,checkout.session.async_payment_succeeded,checkout.session.async_payment_failed --forward-to localhost:8000/v1/pagos/webhook/stripe
   ```

5. Guarda el secreto `whsec_...` que muestra la CLI en `STRIPE_WEBHOOK_SECRET`.
   Debe corresponder a ESE listener. No sirve el secreto de otro endpoint del Dashboard.
   Mantener la terminal de `stripe listen` abierta mientras se hace el pago.
6. Desde `backend`, aplicar el archivo .env a los dos procesos:

   ```bash
   docker compose up -d --build --force-recreate --no-deps backend event_worker payment_worker
   ```

   RabbitMQ debe estar iniciado. Si todavia no lo esta: `docker compose up -d rabbitmq`.
   Reiniciar solo el proceso no recarga env_file: recrear los contenedores tras cambiar claves.
7. Inicia el frontend, inicia sesion y confirma un pedido desde el carrito. Si faltan precios,
   la pantalla actual permite excluirlos explicitamente siempre que haya productos cotizados.
   El panel de Pago muestra los problemas de configuracion y mantiene deshabilitado el boton
   hasta que las claves, URLs y modo TEST sean validos.
8. Solicita el pago, espera el enlace y pulsa Continuar en Stripe. Para exito usa
   `4242 4242 4242 4242`, fecha futura y CVC de prueba. Para tarjeta rechazada usa
   `4000 0000 0000 0002`: el formulario permite corregirla y reintentar.
9. Tras pagar, la app recupera el pedido en el carrito y espera el resultado recibido por webhook.
   Cancelar no marca un fallo ni un exito; permite continuar la misma sesion.
10. Comprueba en el Dashboard de Stripe TEST y en el panel que el importe coincide con
    el total del pedido en COP. Comprueba tambien la fila en Supabase > Table Editor > Pagos.
    Desactiva PAYMENTS_SANDBOX_FIXTURES al terminar si se
    desea bloquear nuevos intentos. No utilizar claves live con este modulo.

Las claves personales permanecen vacias en .env-example y deben obtenerse de la cuenta
Stripe. El ejemplo documenta todas las variables; no contiene credenciales utilizables.
En esta integracion de Checkout hospedado no se necesita clave publica en el frontend.

## Pruebas automaticas

Desde `backend`, con las dependencias del proyecto instaladas:

```bash
python -m unittest discover -s tests -v
```

Las pruebas de pagos usan SQLite real en directorios temporales, HTTP simulado de Stripe,
firmas HMAC reales y endpoints FastAPI. Comprueban reinicio, caidas, duplicados, recuperacion,
importes manipulados, eventos fuera de orden, actualizacion por eventos y aislamiento de usuario.
Las pruebas del adaptador Supabase simulan caidas antes y despues del commit, reentrega,
eventos alterados, filas en conflicto y recuperacion tras migrar la proyeccion local.
No son un cobro ejecutado contra Stripe real.

Prueba adicional con RabbitMQ REAL, en colas y exchange aislados que se eliminan al terminar:

```bash
docker compose run --rm -e PAYMENTS_BROKER_TEST=1 backend python -m unittest discover -s tests -p test_payments_broker.py -v
```

Comprueba envio al broker, fallo temporal de pasarela simulada, reentrega diferida real,
recuperacion y proyeccion del pago por evento. Requiere RabbitMQ iniciado. Esta prueba no
se ejecuta en la suite normal y no accede a Stripe ni a Supabase.

Documentacion oficial consultada:
- https://docs.stripe.com/api/checkout/sessions/create
- https://docs.stripe.com/checkout/fulfillment
- https://docs.stripe.com/events/manage-webhook-endpoints
- https://docs.stripe.com/api/idempotent_requests
