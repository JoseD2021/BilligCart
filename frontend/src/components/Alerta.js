import React from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { colors, radius, spacing, typography } from "../theme/theme";

export default function Alerta({ titulo, mensaje, onCerrar }) {
  if (!titulo && !mensaje) return null;
  return (
    <View style={styles.contenedor}>
      <View style={{ flex: 1 }}>
        {!!titulo && <Text style={styles.titulo}>{titulo}</Text>}
        {!!mensaje && <Text style={styles.mensaje}>{mensaje}</Text>}
      </View>
      <TouchableOpacity onPress={onCerrar} hitSlop={8} accessibilityLabel="Cerrar aviso">
        <Text style={styles.cerrar}>×</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  contenedor: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: spacing.sm,
    backgroundColor: "#FCEAE6",
    borderLeftWidth: 4,
    borderLeftColor: colors.warning,
    borderRadius: radius.sm,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  titulo: { color: colors.warning, fontSize: 14, fontWeight: "700" },
  mensaje: { ...typography.body, fontSize: 13, marginTop: 2 },
  cerrar: { color: colors.warning, fontSize: 20, fontWeight: "700", lineHeight: 20 },
});
