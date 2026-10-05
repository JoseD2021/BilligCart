import React from "react";
import { View, ActivityIndicator } from "react-native";
import { NavigationContainer } from "@react-navigation/native";
import { useAuth } from "../context/AuthContext";
import { colors } from "../theme/theme";
import AuthNavigator from "./AuthNavigator";
import AppTabs from "./AppTabs";

export default function RootNavigator() {
  const { estaAutenticado, cargandoSesion } = useAuth();

  if (cargandoSesion) {
    return (
      <View style={{ flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.background }}>
        <ActivityIndicator color={colors.primary} size="large" />
      </View>
    );
  }

  return (
    <NavigationContainer>
      {estaAutenticado ? <AppTabs /> : <AuthNavigator />}
    </NavigationContainer>
  );
}
