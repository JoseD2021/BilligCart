# Pagos con Stripe

El modulo implementa Checkout, confirmaciones firmadas, solicitudes duraderas y eventos.
No usa los precios de referencia de Compras para cobrar ni modifica el esquema de Supabase.

## Flujo

1. El usuario solicita pagar un pedido: `POST /api/v1/pagos`, con token de sesion,
   `Idempotency-Key` y `{ "order_id": "UUID" }`. El cuerpo no admite importes.
2. `QuoteSource` debe autorizar al propietario y entregar el total definitivo en unidades
   menores de la moneda, version y vencimiento. La implementacion por defecto responde
   `409`: los precios finales y la base de datos de negocio aun no estan listos.
3. Se guardan el intento y `payments.requested.v1` juntos en un registro tecnico SQLite.
   La API responde `202 queued`; eso significa solicitud recibida, NO pago exitoso.
4. El worker publica la outbox en RabbitMQ con confirmaciones del broker. Las colas son
   duraderas, los mensajes persistentes y los reintentos diferidos (5, 30 y 300 segundos).
   Stripe temporalmente caido conserva la misma solicitud y la misma clave de idempotencia.
   RabbitMQ caido conserva los mensajes en la outbox para enviarlos al recuperarse.
5. El worker crea una sesion de Stripe Checkout. El cliente consulta
   `GET /api/v1/pagos/pedido/{order_id}` y abre `checkout_url`. Las tarjetas se introducen
   en Stripe; BilligCart no recibe ni guarda sus datos.
6. Stripe llama a `POST /api/v1/pagos/webhook/stripe`. Se comprueban firma HMAC, antiguedad,
   modo test/live, pedido interno, sesion, moneda e importe. La redireccion del navegador
   nunca marca el pedido como pagado. `completed` sin `paid` queda en `processing`.
7. El webhook guarda estado, deduplicacion y `payments.succeeded.v1` atomicamente.
   El cliente obtiene `succeeded` y muestra el mensaje de pago exitoso.
8. Un consumidor independiente aplica el evento a la proyeccion local `paid_orders` una
   sola vez. Si falla, el evento se reintenta. `PaymentProjection` define donde conectar
   la actualizacion de la futura base de negocio; su adaptador debera deduplicar y actualizar
   el pedido en una sola transaccion. Actualmente NO actualiza la tabla Pedidos de Supabase.

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

`PAYMENTS_JOURNAL_PATH` es un registro tecnico del modulo de pagos, separado de Supabase.
En Compose, API y worker comparten el volumen `payment-journal`; RabbitMQ usa `rabbitmq-data`.
Conservar ambos volumenes. `docker compose down -v` elimina esos datos.
El SQLite compartido es una solucion de un solo host; para replicas en multiples hosts
se debe sustituir por almacenamiento transaccional compartido y mantener la outbox/inbox.
No se almacenan tarjetas. El modulo no implementa reembolsos, disputas ni entrega/reparto.

## Prueba manual en Stripe TEST

1. Configura `STRIPE_SECRET_KEY=sk_test_...` en `backend/.env`.
2. Solo para pruebas, activa `PAYMENTS_SANDBOX_FIXTURES=true`. Usa una cotizacion ficticia
   fija de **1000 unidades menores USD (10 USD de prueba)**. No consulta pedidos reales
   ni verifica su existencia; el aislamiento por usuario es del registro de prueba.
   Esta opcion rechaza claves live. No se habilita por defecto.
3. Configura `STRIPE_SUCCESS_URL` y `STRIPE_CANCEL_URL` con la URL de tu frontend.
4. Inicia Stripe CLI:

   ```bash
   stripe listen --forward-to localhost:8000/v1/pagos/webhook/stripe
   ```

5. Guarda el secreto `whsec_...` que muestra la CLI en `STRIPE_WEBHOOK_SECRET` y reinicia
   la API. No es el mismo secreto que el de otro endpoint del Dashboard.
6. Desde `backend`: `docker compose up -d --build backend rabbitmq payment_worker`.
   El frontend muestra el panel de pago dentro de Pedido cuando hay un pedido disponible.
   Tambien se puede probar la API con un UUID de prueba y un token de sesion valido.
7. Abre el Checkout y usa las tarjetas oficiales de prueba. Comprueba que, tras el webhook,
   el GET devuelve `succeeded`. Volver a la pantalla sin pagar mantiene el intento pendiente.
8. Desactiva las cotizaciones ficticias al terminar. El modo normal vuelve a bloquear
   cobros hasta implementar `QuoteSource` con precios finales y propiedad del pedido.

## Pruebas automaticas

Desde `backend`, con las dependencias del proyecto instaladas:

```bash
python -m unittest discover -s tests -v
```

Las pruebas de pagos usan SQLite real en directorios temporales, HTTP simulado de Stripe,
firmas HMAC reales y endpoints FastAPI. Comprueban reinicio, caidas, duplicados, recuperacion,
importes manipulados, eventos fuera de orden, actualizacion por eventos y aislamiento de usuario.
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
