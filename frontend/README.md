# Frontend — Planificador de Comidas y Presupuesto (React Native + Expo)

Cliente móvil que consume el Backend (FastAPI). Construido desde cero para
este proyecto, sin plantilla externa.

## Estructura

```
frontend/
├── App.js
└── src/
    ├── theme/theme.js          # colores, tipografía, espaciados
    ├── services/api.js         # cliente hacia el backend
    ├── components/Card.js      # tarjeta reutilizable
    ├── navigation/AppNavigator.js
    └── screens/
        ├── PreferenciasScreen.js   # restricciones y presupuesto
        ├── MenuSemanalScreen.js    # menú generado
        ├── ListaComprasScreen.js   # lista optimizada + confirmar/pagar
        └── PedidoScreen.js         # estado de entrega (servicio Repartidores)
```

## Cómo correrlo

1. Instalar dependencias:
   ```
   npm install
   ```
2. Levantar el proyecto con Expo:
   ```
   npx expo start
   ```
3. Escanear el QR con la app **Expo Go** (Android/iOS), o presionar `a`
   para abrir en un emulador de Android.

## Conectar con el backend

Editar `src/services/api.js` y cambiar `BASE_URL` por la URL real donde
corre el Backend/API Gateway (por defecto apunta a `http://localhost:8000`).

Mientras el backend no esté disponible, cada pantalla usa datos de ejemplo
(`DEMO`) como respaldo, para poder seguir desarrollando la interfaz de
forma independiente.

## Próximos pasos sugeridos

- Reemplazar los iconos de emoji por una librería de íconos (ej. `@expo/vector-icons`).
- Agregar pantalla de login/autenticación.
- Conectar notificaciones push para el estado del pedido.
