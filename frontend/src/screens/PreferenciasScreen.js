import React, { useEffect, useState } from "react";
import { View, Text, TextInput, TouchableOpacity, ScrollView, StyleSheet } from "react-native";
import Card from "../components/Card";
import { colors, spacing, radius, typography } from "../theme/theme";
import { useAuth } from "../context/AuthContext";
import { getPreferencias, guardarPreferencias } from "../services/preferenciasService";

const RESTRICCIONES = ["Vegetariano", "Vegano", "Sin gluten", "Sin lactosa", "Sin frutos secos"];

export default function PreferenciasScreen() {
  const { usuario, cerrarSesion } = useAuth();
  const [restricciones, setRestricciones] = useState([]);
  const [presupuesto, setPresupuesto] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [mensaje, setMensaje] = useState(null); // { ok, texto }

  // Carga lo que el usuario ya guardó antes.
  useEffect(() => {
    if (!usuario?.id) return;
    getPreferencias(usuario.id)
      .then((p) => {
        if (!p) return;
        setRestricciones(p.restricciones ?? []);
        setPresupuesto(p.presupuesto_semanal ? String(p.presupuesto_semanal) : "");
      })
      .catch((e) => console.warn("getPreferencias:", e.message));
  }, [usuario?.id]);

  function toggleRestriccion(item) {
    setRestricciones((prev) =>
      prev.includes(item) ? prev.filter((r) => r !== item) : [...prev, item]
    );
  }

  async function guardar() {
    setGuardando(true);
    setMensaje(null);
    try {
      await guardarPreferencias(usuario.id, {
        restricciones,
        // Acepta "150.000" o "150000": se dejan solo los dígitos.
        presupuesto_semanal: Number(presupuesto.replace(/\D/g, "")) || 0,
      });
      setMensaje({ ok: true, texto: "Preferencias guardadas. Tu próximo menú las tendrá en cuenta." });
    } catch (e) {
      console.warn("guardarPreferencias:", e.message);
      setMensaje({ ok: false, texto: "No se pudieron guardar. Revisa tu conexión e intenta de nuevo." });
    } finally {
      setGuardando(false);
    }
  }

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <Text style={typography.h1}>Tus preferencias</Text>
      <Text style={[typography.bodyMuted, { marginBottom: spacing.lg }]}>
        Esto define cómo se arma tu menú y tu lista de compras.
      </Text>

      <Card>
        <Text style={typography.h2}>Restricciones alimentarias</Text>
        <View style={styles.chipsRow}>
          {RESTRICCIONES.map((item) => {
            const activo = restricciones.includes(item);
            return (
              <TouchableOpacity
                key={item}
                onPress={() => toggleRestriccion(item)}
                style={[styles.chip, activo && styles.chipActivo]}
              >
                <Text style={[styles.chipText, activo && styles.chipTextActivo]}>{item}</Text>
              </TouchableOpacity>
            );
          })}
        </View>
      </Card>

      <Card>
        <Text style={typography.h2}>Presupuesto semanal</Text>
        <Text style={[typography.bodyMuted, { marginBottom: spacing.sm }]}>
          Usamos esto para priorizar ofertas y ajustar la lista de compras.
        </Text>
        <View style={styles.inputRow}>
          <Text style={styles.currencyPrefix}>$</Text>
          <TextInput
            value={presupuesto}
            onChangeText={setPresupuesto}
            placeholder="150.000"
            keyboardType="numeric"
            style={styles.input}
            placeholderTextColor={colors.textMuted}
          />
        </View>
      </Card>

      <TouchableOpacity style={styles.botonGuardar} onPress={guardar} disabled={guardando}>
        <Text style={styles.botonGuardarTexto}>
          {guardando ? "Guardando..." : "Guardar preferencias"}
        </Text>
      </TouchableOpacity>

      {mensaje && (
        <Text style={[styles.mensaje, { color: mensaje.ok ? colors.primary : colors.warning }]}>
          {mensaje.texto}
        </Text>
      )}

      <TouchableOpacity style={styles.botonCerrarSesion} onPress={cerrarSesion}>
        <Text style={styles.botonCerrarSesionTexto}>Cerrar sesión</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: spacing.xl },
  chipsRow: { flexDirection: "row", flexWrap: "wrap", marginTop: spacing.sm },
  chip: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.pill,
    paddingVertical: spacing.xs,
    paddingHorizontal: spacing.md,
    marginRight: spacing.sm,
    marginBottom: spacing.sm,
    backgroundColor: colors.background,
  },
  chipActivo: { backgroundColor: colors.primary, borderColor: colors.primary },
  chipText: { color: colors.text, fontSize: 13 },
  chipTextActivo: { color: colors.white, fontWeight: "600" },
  inputRow: {
    flexDirection: "row",
    alignItems: "center",
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.sm,
    paddingHorizontal: spacing.md,
  },
  currencyPrefix: { color: colors.textMuted, marginRight: spacing.xs, fontSize: 16 },
  input: { flex: 1, paddingVertical: spacing.sm, fontSize: 16, color: colors.text },
  botonGuardar: {
    backgroundColor: colors.primary,
    borderRadius: radius.md,
    paddingVertical: spacing.md,
    alignItems: "center",
    marginTop: spacing.md,
  },
  botonGuardarTexto: { color: colors.white, fontWeight: "700", fontSize: 15 },
  mensaje: { marginTop: spacing.sm, fontSize: 13, fontWeight: "600", textAlign: "center" },
  botonCerrarSesion: {
    alignItems: "center",
    paddingVertical: spacing.md,
    marginTop: spacing.sm,
  },
  botonCerrarSesionTexto: { color: colors.warning, fontWeight: "600", fontSize: 14 },
});
