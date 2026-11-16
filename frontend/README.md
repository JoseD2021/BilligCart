

## Estructura

```
frontend/
├── App.js
└── src/
    ├── theme/theme.js          # colores, tipografía, espaciados
    ├── services/api.js         # cliente hacia el backend
    ├── components/Card.js      # tarjeta reutilizable
    ├── navigation/RootNavigator.js # sesión, autenticación y pestañas
    └── screens/
        ├── PreferenciasScreen.js   # restricciones y presupuesto
        ├── MenuSemanalScreen.js    # menú generado
        ├── ListaComprasScreen.js   # ingredientes del menú + registrar pedido
        └── PedidoScreen.js         # estado persistido del pedido propio
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
   para abrir en un emulador de Android o npx expo start -c --web y te manda a la web.

Supabase se utiliza exclusivamente para autenticación y renovación de sesión. Preferencias, menú, compras y pedidos se consultan mediante el backend. Ejecuta primero la migración indicada en el README principal.

En web, el proxy usa el backend local en el puerto 8000. En un dispositivo móvil, configura `EXPO_PUBLIC_API_URL` con la dirección del servidor accesible desde el teléfono. Las pantallas muestran estados vacíos y errores reales; no sustituyen fallos por datos de ejemplo.
