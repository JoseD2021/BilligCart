import React from "react";
import { View, Text, ScrollView, StyleSheet } from "react-native";
import Card from "../components/Card";
import { colors, spacing, radius, typography } from "../theme/theme";

const MOMENTOS = [
  { clave: "desayuno", titulo: "Desayuno", icono: "☀️" },
  { clave: "almuerzo", titulo: "Almuerzo", icono: "🍲" },
  { clave: "cena", titulo: "Cena", icono: "🌙" },
];

function formatoCantidad(ing) {
  if (ing.cantidad == null) return "";
  return `${ing.cantidad} ${ing.unidad ?? ""}`.trim();
}

export default function DiaMenuScreen({ route }) {
  const { dia } = route.params;
  const n = Object.keys(dia.comidas).length;

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <Text style={typography.h1}>{dia.dia}</Text>
      <Text style={[typography.bodyMuted, { marginBottom: spacing.lg }]}>
        {n === 0 ? "Sin comidas planeadas" : `${n} ${n === 1 ? "comida planeada" : "comidas planeadas"}`}
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
            {!!comida.descripcion && (
              <Text style={[typography.bodyMuted, { marginTop: spacing.xs }]}>{comida.descripcion}</Text>
            )}

            {comida.ingredientes.length > 0 && (
              <View style={styles.bloqueIngredientes}>
                <Text style={typography.label}>INGREDIENTES</Text>
                {comida.ingredientes.map((ing, i) => (
                  <View key={i} style={styles.filaIngrediente}>
                    <View style={{ flex: 1 }}>
                      <Text style={typography.body}>{ing.nombre}</Text>
                      <Text style={typography.bodyMuted}>
                        {[formatoCantidad(ing), ing.tienda].filter(Boolean).join(" · ")}
                      </Text>
                    </View>
                    {ing.precio != null && (
                      <Text style={typography.price}>${Number(ing.precio).toLocaleString("es-CO")}</Text>
                    )}
                  </View>
                ))}
              </View>
            )}
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
  bloqueIngredientes: {
    marginTop: spacing.md,
    paddingTop: spacing.md,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  filaIngrediente: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: spacing.sm,
  },
});
