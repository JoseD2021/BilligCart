

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
   para abrir en un emulador de Android o npx expo start -c --web y te manda a la web.


