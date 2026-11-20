import React from "react";
import { View, Text, TextInput, StyleSheet } from "react-native";
import { colors, spacing, radius, typography } from "../theme/theme";

/**
 * ESPACIO PARA EL GPS  (lo implementa el compañero)
 *
 * Contrato:
 *   props.value    -> { direccion: string, referencia: string, lat: number|null, lng: number|null }
 *   props.onChange -> (nuevoValue) => void
 *
 * Mientras tanto funciona con dirección escrita a mano. Para meter el mapa/GPS basta con
 * reemplazar el bloque marcado abajo y llamar onChange({ ...value, lat, lng, direccion }).
 * El resto del carrito no necesita cambios.
 */
export default function SelectorUbicacion({ value, onChange }) {
  return (
    <View>
      {/* ===== AQUÍ VA EL MAPA / GPS ===== */}
      <View style={styles.espacioMapa}>
        <Text style={typography.bodyMuted}>📍 Aquí irá el mapa con la ubicación (GPS)</Text>
      </View>
      {/* ================================= */}

      <Text style={typography.label}>DIRECCIÓN DE ENTREGA</Text>
      <TextInput
        style={styles.input}
        placeholder="Calle 100 # 15-20, apto 301"
        placeholderTextColor={colors.textMuted}
        value={value.direccion}
        onChangeText={(direccion) => onChange({ ...value, direccion })}
      />
      <Text style={[typography.label, { marginTop: spacing.md }]}>REFERENCIA (OPCIONAL)</Text>
      <TextInput
        style={styles.input}
        placeholder="Portería, torre, punto de referencia..."
        placeholderTextColor={colors.textMuted}
        value={value.referencia}
        onChangeText={(referencia) => onChange({ ...value, referencia })}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  espacioMapa: {
    height: 180,
    borderRadius: radius.md,
    borderWidth: 1,
    borderStyle: "dashed",
    borderColor: colors.border,
    backgroundColor: colors.surface,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: spacing.lg,
  },
  input: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.sm,
    padding: spacing.md,
    marginTop: spacing.xs,
    fontSize: 15,
    color: colors.text,
  },
});
