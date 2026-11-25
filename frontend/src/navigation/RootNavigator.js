import React, { useCallback, useEffect, useRef } from "react";
import { View, ActivityIndicator, Linking } from "react-native";
import { NavigationContainer, useNavigationContainerRef } from "@react-navigation/native";
import { useAuth } from "../context/AuthContext";
import { colors } from "../theme/theme";
import AuthNavigator from "./AuthNavigator";
import AppTabs from "./AppTabs";
import { paymentOrderFromUrl } from "../services/paymentReturn";

export default function RootNavigator() {
  const { estaAutenticado, cargandoSesion } = useAuth();
  const navigation = useNavigationContainerRef();
  const pendingOrder = useRef(null);
  const handleReturn = useCallback(() => {
    if (estaAutenticado && pendingOrder.current && navigation.isReady()) {
      const paymentOrderId = pendingOrder.current;
      pendingOrder.current = null;
      navigation.navigate("Compras", { paymentOrderId });
    }
  }, [estaAutenticado, navigation]);

  useEffect(() => {
    let active = true;
    const receive = (url) => {
      const order = paymentOrderFromUrl(url);
      if (active && order) { pendingOrder.current = order; handleReturn(); }
    };
    Linking.getInitialURL().then(receive).catch(() => {});
    const subscription = Linking.addEventListener("url", ({ url }) => receive(url));
    handleReturn();
    return () => { active = false; subscription.remove(); };
  }, [handleReturn]);

  if (cargandoSesion) {
    return (
      <View style={{ flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.background }}>
        <ActivityIndicator color={colors.primary} size="large" />
      </View>
    );
  }

  return (
    <NavigationContainer ref={navigation} onReady={handleReturn}>
      {estaAutenticado ? <AppTabs /> : <AuthNavigator />}
    </NavigationContainer>
  );
}
