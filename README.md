# BilligCart

La integracion de pagos con Stripe, sus limites actuales y las instrucciones de prueba
estan documentados en [backend/PAYMENTS.md](backend/PAYMENTS.md). En Stripe TEST se utiliza
el total del pedido en COP; las claves live permanecen bloqueadas mientras los precios
sigan siendo de referencia. Completa las claves personales indicadas en backend/.env-example.

BilligCart es una aplicación que genera menús semanales con inteligencia artificial, consulta productos de supermercados para encontrar precios y guarda la información del menú y sus ingredientes en Supabase.

## Tecnologías

- **Backend:** Python y FastAPI.
- **Frontend:** React Native con Expo, puerto `8081`.
- **Base de datos:** Supabase.
- **Mensajería y eventos:** RabbitMQ.
- **Generación con IA:** Ollama.
- **Ejecución de servicios:** Docker Compose.

## Arquitectura

El backend está organizado por capas para separar las reglas del negocio, los casos de uso y los detalles técnicos:

- **Domain:** entidades y reglas centrales del negocio.
- **Application:** casos de uso y coordinación de la lógica de la aplicación.
- **Infrastructure:** integración con servicios externos, mensajería y persistencia.

Además, el proyecto emplea los siguientes patrones y flujos de arquitectura.

### Visitor: cálculo de costes y estadísticas

El cálculo de costes se mantiene separado de la definición de los productos. Cada ingrediente contiene la información necesaria para calcular su coste, como la cantidad, la unidad de medida y el precio por unidad. Los ingredientes se reúnen en una colección y se recorren para obtener el coste total mediante `getCostoTotal()`.

Esta separación facilita calcular costes o estadísticas para distintos tipos de productos sin concentrar toda la lógica en la definición de cada uno. El cálculo puede trabajar con cantidades expresadas en distintas unidades de medida —por ejemplo, gramos, kilogramos, libras o litros— aplicando las conversiones necesarias para obtener resultados comparables. No se trata de convertir monedas, sino de gestionar las unidades de medida de los ingredientes.

### Builder y Director: extracción de productos de supermercados

El endpoint autenticado `POST /api/v1/ingrediente/fetch/{id}` inicia la búsqueda de productos para un ingrediente. Cualquier usuario con sesión puede usarlo: el backend vuelve a validar que el último fetch tenga más de 7 días antes de scrapear. El frontend solo lo llama cuando `GET /compras` reporta una cotización vieja (o nunca hecha) para ese ingrediente.

1. Se define un **Builder (scraper)** para cada supermercado compatible.
2. Se instancia un **Director** asociado a ese Builder y se llama a `process_list(RAW_JSON)`, donde `RAW_JSON` es la respuesta recibida de la API del supermercado.
3. El Director coordina las funciones del Builder que extraen los datos relevantes, como el nombre del producto, el precio y la URL.
4. Cada Builder transforma los resultados al formato común de ingrediente que utiliza el resto de la aplicación.
5. Fuera del Builder, el caso de uso compara los productos encontrados, selecciona el de menor precio y guarda el resultado en la base de datos.

La lógica de búsqueda y normalización se encuentra en `src/application/commands/ingrediente/scrape_ingrediente`. Estandarizar los datos permite procesar de la misma forma productos obtenidos de distintas APIs de supermercados.

### Eventos y mensajería con RabbitMQ

La generación del menú utiliza mensajería asíncrona y eventos para separar la respuesta de la IA de la persistencia del resultado.

1. El backend envía la solicitud a la cola `ai_requests` y espera la respuesta mediante `reply_to` y `correlation_id`.
2. `ai_worker` consume la solicitud, llama a Ollama y devuelve el resultado al backend.
3. Durante el proceso, `ai_worker` publica eventos de inicio, finalización o error de generación en el exchange `domain_events`.
4. En `POST /menu/generate`, la API lee las preferencias, construye el prompt, espera la IA y persiste las 21 comidas antes de responder. El evento lleva `persist_via_events=false` para evitar guardar dos veces.
5. La ruta anterior `POST /ai/generate` conserva la persistencia asíncrona mediante `event_worker`, con `persist_via_events=true` por defecto.
6. Los eventos que no se pueden procesar se derivan a la cola de mensajes fallidos (dead-letter queue) configurada en RabbitMQ.

Los contratos, la publicación, el registro de handlers y la integración con RabbitMQ están organizados en `src/events/`. El frontend utiliza `/menu/generate` y recibe el menú persistido, sin comparar nombres ni consultar tablas de Supabase.

## Puertos y servicios

| Servicio | Dirección | Uso |
|---|---|---|
| Frontend | `http://localhost:8081` | Interfaz de usuario expo (pc local)|
| Backend | `http://localhost` | API REST |
| Swagger | `http://localhost/docs` | Documentación interactiva a través de Traefik |
| RabbitMQ AMQP | `localhost:5672` | Comunicación entre servicios |
| Panel de RabbitMQ | `http://localhost:15672` *(solo si está habilitado el plugin y publicado el puerto)* | Administración y monitoreo |

Dentro de Docker Compose, los servicios deben comunicarse usando el nombre del servicio. Por ejemplo, el backend se conecta a RabbitMQ mediante `rabbitmq:5672`, no mediante `localhost:5672`. El `.env.example` confirma el puerto AMQP `5672`; no confirma por sí solo que el panel web esté habilitado.

## Requisitos

- **Backend:** Docker y Docker Compose.
- **Frontend:** Node.js (versión LTS) y npm, que se instala junto con Node.js.
- Un proyecto de Supabase y sus credenciales.
- Un archivo `.env` configurado a partir de `.env.example`.
- Para probar la app en un dispositivo móvil, un entorno compatible con Expo (por ejemplo, Expo Go si es compatible con el SDK del proyecto, o un emulador configurado).

El frontend utiliza Expo. Si en `frontend/package.json` aparece `"expo": "~51.0.0"`, esa es la versión de Expo SDK que debe respetarse al instalar las dependencias; no instales `expo@latest` por separado, ya que podría generar incompatibilidades. Expo SDK 51 es una versión antigua, por lo que conviene comprobar la compatibilidad del entorno de ejecución con esa versión.

## Configuración

1. Clona el repositorio y entra en la carpeta del proyecto.
2. Crea un archivo `.env` usando `.env.example` como referencia.
3. Sustituye los valores de ejemplo por tus credenciales. No subas el `.env` ni publiques claves o contraseñas reales.
4. Ejecuta en el editor SQL de Supabase, en orden, `backend/migrations/001_backend_owned_flows.sql`, `002_unify_pedido_estado.sql` y `003_roles.sql`. Añaden preferencias, pedidos y roles, unifican el estado del pedido y restringen el acceso directo a las tablas.
5. Usa una clave de servidor (`service_role` o `sb_secret_...`) en `SUPABASE_KEY`. El frontend solo necesita una clave pública de Supabase Auth; las consultas de negocio usan la API.

Las variables definidas en `.env.example` son:

```env
SUPABASE_URL=https://XXXXXXXXXXXX.supabase.co
SUPABASE_KEY=SECRET_KEY

RABBITMQ_USER=XXXXXXXX
RABBITMQ_PASSWORD=XXXXXXXX
RABBITMQ_QUEUE=ai_requests
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672

OLLAMA_MODEL=gemma4:e4b

RABBITMQ_EVENT_EXCHANGE=domain_events
RABBITMQ_EVENT_DEAD_LETTER_EXCHANGE=domain_events.dlx
RABBITMQ_EVENT_QUEUE=application_events
RABBITMQ_VHOST=/
```

Asegúrate de que Ollama tenga disponible el modelo indicado por `OLLAMA_MODEL`.

Al levantar el backend, `ollama-init` descarga el modelo y lo precarga en VRAM con `keep_alive=-1`; además, el servicio `ollama` usa `OLLAMA_KEEP_ALIVE=-1`, por lo que el modelo no se descarga por inactividad. Verifícalo con `docker compose exec ollama ollama ps`: la columna `UNTIL` debe indicar `Forever`. Si Ollama se reinicia, el cliente carga el modelo de nuevo en la primera solicitud y lo mantiene con la misma retención.

## Ejecución

El backend y el frontend se ejecutan desde **dos terminales distintas**.

### 1. Backend y servicios Docker

En la primera terminal, entra en la carpeta `backend` y ejecuta allí los comandos de Docker Compose:

```bash
cd backend
docker compose up -d --build
```

Para consultar los registros de los servicios principales (también desde `backend`):

```bash
docker compose logs -f backend ai_worker event_worker payment_worker
```

Para detener los servicios, ejecuta desde esa misma carpeta:

```bash
docker compose down
```

### 2. Frontend con Expo

En una segunda terminal, entra en la carpeta `frontend`, instala las dependencias y arranca Expo:

```bash
cd frontend
npm install
npx expo start
# para usar por expo go (sdk 51):
npx expo start --tunnel --clear
```

`npm install` descarga las dependencias declaradas por el proyecto. `npx expo start` inicia el servidor de desarrollo y muestra un código QR o las opciones para abrir la aplicación en un emulador compatible. Para abrirla en un teléfono, el dispositivo y el ordenador normalmente deben estar en la misma red Wi-Fi.

En la demo web, el HTTP usa el proxy de Metro en `/api/v1` y los WebSocket van directo a Traefik en el puerto 80 (`ws://<host>/ws/...`). En móvil se usa `EXPO_PUBLIC_WS_URL` o, si no está definida, se deriva de `EXPO_PUBLIC_API_URL`.

## Generación y persistencia del menú

El menú semanal contempla siete días con desayuno, almuerzo y cena: **21 platos en total**. Ollama genera el menú a través de `ai_worker`; la API valida y guarda el resultado antes de devolverlo al frontend. Si falla la lectura de preferencias, la generación se detiene para no omitir restricciones alimentarias.

## Acceso y rutas de la aplicación

Las rutas de negocio requieren `Authorization: Bearer <access_token>`. Los recursos de menú, plato, relación y pedido se verifican contra el usuario autenticado; nunca se toma el propietario del cuerpo de la solicitud. Los ingredientes son un catálogo compartido: cualquier usuario autenticado puede consultarlo y actualizar precios con `POST /ingrediente/fetch/{id}`, pero crear, editar o borrar ingredientes requiere `rol = "admin"` en la tabla `public."Roles"` (clave primaria `user_id` = UID de Supabase Auth), asignada desde un servidor de confianza. El registro elige solo entre `user` y `repartidor` (`POST /auth/register` con `role`), lo escribe en `Roles` con la clave de servicio y devuelve el token de sesión cuando Supabase no exige confirmación de correo; `admin` no se puede autoasignar. `GET /auth/me` devuelve ese mismo rol. No se utiliza `user_metadata` ni `app_metadata` para conceder permisos.

| Ruta relativa a `/api/v1` | Uso |
|---|---|
| `POST /auth/register` | Crear usuario con `role: "user"` o `"repartidor"` y persistirlo en `Roles` |
| `GET /auth/me` | Usuario autenticado con su rol desde `Roles` |
| `GET /menu/weekly` | Menú completo del usuario, con platos e ingredientes |
| `POST /menu/generate` | Generar con preferencias y devolver el resultado persistido |
| `GET /preferencias`, `PUT /preferencias` | Consultar y guardar las preferencias propias |
| `GET /compras` | Ingredientes agregados del menú actual y `ultimos_fetch` por id de ingrediente |
| `POST /ingrediente/fetch/{id}` | Buscar ofertas y actualizar el precio de referencia de un ingrediente |
| `POST /compras/confirmar` | Registrar un pedido con una copia de la lista; `omitir_sin_precio: true` excluye ingredientes sin cotizar; reintentar la misma lista no duplica el pedido |
| `GET /pedidos/current` | Último pedido propio, o `null` |
| `GET /pedidos/{id}/estado` | Consultar un pedido propio |

Compras muestra cantidades agregadas y precios de referencia del catálogo. Los precios existentes no incluyen tamaño de empaque: su suma no representa un cobro calculado por gramos o mililitros. Con `ultimos_fetch`, el frontend solicita una nueva cotización solo para los ingredientes sin fetch o con más de 7 días, tanto en Lista de compras como en Carrito; ante un fallo individual lo reintenta cuando el usuario vuelve a entrar o pulsa "Actualizar precios". La confirmación requiere el menú completo. Si faltan precios, el usuario puede marcar explícitamente `omitir_sin_precio` en Carrito para pagar solo los ingredientes cotizados: el pedido y su total excluyen los pendientes. Registra el pedido; no procesa pagos ni asigna repartidores. Pedido muestra el estado guardado (`pendiente`, `confirmado`, `en_camino`, `entregado`) y el repartidor cuando está asignado. El antiguo campo `tiempo_estimado` ya no se utiliza. La columna `estado` es la única fuente de verdad; la migración `002_unify_pedido_estado.sql` elimina la antigua columna `etapa` y migra sus valores.

La API registra método, ruta, estado, duración e identificador de solicitud, que también devuelve en `X-Request-ID`. No registra contraseñas, tokens ni cuerpos. Los detalles de errores de persistencia quedan en los logs del servidor.

Se eliminaron `PUT /menu/update`, el archivo vacío `get_current_user.py`, el navegador sin uso `AppNavigator.js` y los datos demo de Compras y Pedido.

## Comprobaciones

Desde `backend`, con las dependencias de `requirements.txt` instaladas:

```bash
python -m unittest discover -s tests -v
```

Las pruebas usan repositorios y servicios externos simulados; cubren reglas del dominio, generación, persistencia, preferencias, compras, autorización, registros de solicitudes y protección ante pedidos duplicados. No necesitan credenciales reales.

Desde `frontend`:

```bash
npx expo export --platform web --output-dir dist --max-workers 1
```

El proxy web de Expo usa `BACKEND_PORT=8000` por defecto y traduce `/api/v1` a `/v1` del backend directo. Docker publica ese puerto únicamente en `127.0.0.1`. En un dispositivo móvil configura `EXPO_PUBLIC_API_URL=http://<IP-del-servidor>/api/v1` usando Traefik en el puerto 80.
