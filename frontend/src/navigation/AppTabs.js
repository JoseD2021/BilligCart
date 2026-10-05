import React from "react";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { Text } from "react-native";

import PreferenciasScreen from "../screens/PreferenciasScreen";
import MenuSemanalScreen from "../screens/MenuSemanalScreen";
import ListaComprasScreen from "../screens/ListaComprasScreen";
import PedidoScreen from "../screens/PedidoScreen";
import { colors } from "../theme/theme";

const Tab = createBottomTabNavigator();

// Iconos simples con emoji para no depender de una librería de íconos
const ICONOS = {
  Menú: "🍽️",
  Compras: "🛒",
  Pedido: "🛵",
  Preferencias: "⚙️",
};

export default function AppTabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarIcon: () => <Text style={{ fontSize: 18 }}>{ICONOS[route.name]}</Text>,
      })}
    >
      <Tab.Screen name="Menú" component={MenuSemanalScreen} />
      <Tab.Screen name="Compras" component={ListaComprasScreen} />
      <Tab.Screen name="Pedido" component={PedidoScreen} />
      <Tab.Screen name="Preferencias" component={PreferenciasScreen} />
    </Tab.Navigator>
  );
}
