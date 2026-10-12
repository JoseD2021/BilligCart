import React from "react";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import MenuSemanalScreen from "../screens/MenuSemanalScreen";
import DiaMenuScreen from "../screens/DiaMenuScreen";
import { colors } from "../theme/theme";

const Stack = createNativeStackNavigator();


export default function MenuStack() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="MenuSemana" component={MenuSemanalScreen} />
      <Stack.Screen
        name="DiaMenu"
        component={DiaMenuScreen}
        options={({ route }) => ({
          headerShown: true,
          title: route.params?.dia?.dia ?? "Menú del día",
          headerTintColor: colors.primary,
          headerStyle: { backgroundColor: colors.background },
          headerShadowVisible: false,
          headerBackTitle: "Menú",
        })}
      />
    </Stack.Navigator>
  );
}
