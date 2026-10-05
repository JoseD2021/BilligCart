import React, { useEffect, useState } from "react";
import { View, Text, ScrollView, StyleSheet, ActivityIndicator } from "react-native";
import Card from "../components/Card";
import { colors, spacing, typography } from "../theme/theme";
import { api } from "../services/api";

const DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];

// Datos de ejemplo mientras el backend no está disponible.
const MENU_DEMO = DIAS.map((dia, i) => ({
  dia,
  receta: ["Lentejas con arroz", "Pollo al horno", "Ensalada de garbanzos", "Pasta integral", "Sopa de verduras", "Tacos de frijol", "Arroz con vegetales"][i],
  calorias: 480 + i * 15,
}));

export default function MenuSemanalScreen({ usuarioId = "demo" }) {
  const [menu, setMenu] = useState(null);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    api
      .getMenuSemanal(usuarioId)
      .then(setMenu)
      .catch(() => setMenu(MENU_DEMO)) // fallback mientras se conecta el backend real
      .finally(() => setCargando(false));
  }, [usuarioId]);

  if (cargando) {
    return (
      <View style={styles.centrado}>
        <ActivityIndicator color={colors.primary} size="large" />
        <Text style={[typography.bodyMuted, { marginTop: spacing.sm }]}>
          Generando tu menú semanal...
        </Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <Text style={typography.h1}>Menú de esta semana</Text>
      <Text style={[typography.bodyMuted, { marginBottom: spacing.lg }]}>
        Armado según tus preferencias y lo que ya tienes en casa.
      </Text>

      {menu.map((item) => (
        <Card key={item.dia} style={styles.filaMenu}>
          <View style={styles.diaBadge}>
            <Text style={styles.diaBadgeTexto}>{item.dia.slice(0, 3).toUpperCase()}</Text>
          </View>
          <View style={{ flex: 1 }}>
            <Text style={typography.h2}>{item.receta}</Text>
            <Text style={typography.bodyMuted}>{item.calorias} kcal aprox.</Text>
          </View>
        </Card>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: spacing.xl },
  centrado: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.background },
  filaMenu: { flexDirection: "row", alignItems: "center" },
  diaBadge: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
    marginRight: spacing.md,
  },
  diaBadgeTexto: { color: colors.white, fontSize: 11, fontWeight: "700" },
});
