import React from "react";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { Text } from "react-native";

import PreferenciasScreen from "../screens/PreferenciasScreen";
import MenuStack from "./MenuStack";
import CarritoScreen from "../screens/CarritoScreen";
import PedidoScreen from "../screens/PedidoScreen";
import RepartidorScreen from "../screens/RepartidorScreen";
import { colors } from "../theme/theme";
import { useAuth } from "../context/AuthContext";

const Tab = createBottomTabNavigator();

const ICONOS = { Menú: "🍽️", Compras: "🛒", Pedido: "🛵", Preferencias: "⚙️", Repartidor: "📍" };

export default function AppTabs() {
  const { usuario } = useAuth();
  const esRepartidor = usuario?.role === "repartidor";
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarIcon: () => <Text style={{ fontSize: 18 }}>{ICONOS[route.name]}</Text>,
      })}
    >
      {esRepartidor ? (
        <>
          <Tab.Screen name="Repartidor" component={RepartidorScreen} />
          <Tab.Screen name="Preferencias" component={PreferenciasScreen} />
        </>
      ) : (
        <>
          <Tab.Screen name="Menú" component={MenuStack} />
          <Tab.Screen name="Compras" component={CarritoScreen} />
          <Tab.Screen name="Pedido" component={PedidoScreen} />
          <Tab.Screen name="Preferencias" component={PreferenciasScreen} />
        </>
      )}
    </Tab.Navigator>
  );
}
