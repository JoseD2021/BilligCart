import React from "react";
import { View, Text, ScrollView, StyleSheet } from "react-native";
import Card from "../components/Card";
import { colors, spacing, radius, typography } from "../theme/theme";

const MOMENTOS = [
  { clave: "desayuno", titulo: "Desayuno", icono: "☀️" },
  { clave: "almuerzo", titulo: "Almuerzo", icono: "🍲" },
  { clave: "cena", titulo: "Cena", icono: "🌙" },
];

export default function DiaMenuScreen({ route }) {
  const { dia } = route.params;
  const total = Object.values(dia.comidas).reduce((s, c) => s + (c.calorias || 0), 0);

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <Text style={typography.h1}>{dia.dia}</Text>
      <Text style={[typography.bodyMuted, { marginBottom: spacing.lg }]}>
        {total} kcal aprox. en el día
      </Text>

      {MOMENTOS.map(({ clave, titulo, icono }) => {
        const comida = dia.comidas[clave];
        if (!comida) return null;
        return (
          <Card key={clave}>
            <View style={styles.encabezado}>
              <View style={styles.iconoCirculo}>
                <Text style={{ fontSize: 18 }}>{icono}</Text>
              </View>
              <Text style={typography.label}>{titulo.toUpperCase()}</Text>
            </View>
            <Text style={typography.h2}>{comida.nombre}</Text>
            <Text style={[typography.bodyMuted, { marginTop: spacing.xs }]}>
              {comida.calorias} kcal aprox.
            </Text>
          </Card>
        );
      })}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: spacing.xl },
  encabezado: { flexDirection: "row", alignItems: "center", marginBottom: spacing.sm },
  iconoCirculo: {
    width: 34,
    height: 34,
    borderRadius: radius.pill,
    backgroundColor: colors.background,
    alignItems: "center",
    justifyContent: "center",
    marginRight: spacing.sm,
  },
});
