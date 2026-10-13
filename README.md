# BilligCart

BilligCart es una aplicación que genera menús semanales con inteligencia artificial, consulta productos de supermercados para encontrar precios y guarda la información del menú y sus ingredientes en Supabase.

## Tecnologías

- **Backend:** Python y FastAPI.
- **Frontend:** puerto `8081`.
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

El endpoint `GET /api/v1/ingrediente/fetch/{id}` inicia el proceso de búsqueda de productos para un ingrediente.

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
4. `event_worker` consume `MenuGenerationCompleted` y ejecuta el caso de uso que guarda el menú y sus ingredientes en Supabase.
5. Los eventos que no se pueden procesar se derivan a la cola de mensajes fallidos (dead-letter queue) configurada en RabbitMQ.

Los contratos, la publicación, el registro de handlers y la integración con RabbitMQ están organizados en `src/events/`. La persistencia del menú es asíncrona, por lo que puede completarse después de que el backend haya respondido a la petición de generación.

## Puertos y servicios

| Servicio | Dirección | Uso |
|---|---|---|
| Frontend | `http://localhost:8081` | Interfaz de usuario |
| Backend | `http://localhost:8000` | API REST |
| Swagger | `http://localhost:8000/docs` | Documentación interactiva de la API |
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
docker compose logs -f backend ai_worker event_worker
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
```

`npm install` descarga las dependencias declaradas por el proyecto. `npx expo start` inicia el servidor de desarrollo y muestra un código QR o las opciones para abrir la aplicación en un emulador compatible. Para abrirla en un teléfono, el dispositivo y el ordenador normalmente deben estar en la misma red Wi-Fi.

## Generación y persistencia del menú

El menú semanal contempla siete días con desayuno, almuerzo y cena: **21 platos en total**. Ollama genera el menú a través de `ai_worker`; después, `event_worker` procesa el evento de finalización y persiste los platos y sus ingredientes en Supabase. Si el menú no aparece guardado inmediatamente, revisa los registros de `ai_worker` y `event_worker`.
