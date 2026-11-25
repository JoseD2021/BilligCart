import React from "react";
import { createNativeStackNavigator } from "@react-navigation/native-stack";

import PedidosScreen from "../screens/PedidosScreen";
import PedidoScreen from "../screens/PedidoScreen";
import { colors } from "../theme/theme";

const Stack = createNativeStackNavigator();

export default function PedidoStack() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="Pedidos" component={PedidosScreen} />
      <Stack.Screen
        name="PedidoDetalle"
        component={PedidoScreen}
        options={{
          headerShown: true,
          title: "Detalle del pedido",
          headerTintColor: colors.primary,
          headerStyle: { backgroundColor: colors.background },
          headerShadowVisible: false,
          headerBackTitle: "Pedidos",
        }}
      />
    </Stack.Navigator>
  );
}
