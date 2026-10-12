import React, { useCallback, useEffect, useState } from "react";
import { View, Text, ScrollView, TouchableOpacity, StyleSheet, ActivityIndicator } from "react-native";
import Card from "../components/Card";
import { colors, spacing, radius, typography } from "../theme/theme";
import { useAuth } from "../context/AuthContext";
import { getMenuSemanal } from "../services/menuService";
import { generarMenuSemanal } from "../services/menuGenerador";

function formatoSemana(iso) {
  if (!iso) return "";
  return new Date(`${iso}T00:00:00`).toLocaleDateString("es-CO", { day: "numeric", month: "long" });
}

export default function MenuSemanalScreen({ navigation }) {
  const { usuario } = useAuth();
  const [menu, setMenu] = useState(null); // null = el usuario aún no tiene menú
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);
  const [generando, setGenerando] = useState(false);
  const [progreso, setProgreso] = useState("");
  const [errorGeneracion, setErrorGeneracion] = useState(null);
  const [confirmando, setConfirmando] = useState(false); // pide confirmar antes de reemplazar el menú

  // Pide al backend que genere el menú de la semana (desayuno, almuerzo y cena de cada día).
  async function generar() {
    setConfirmando(false);
    setErrorGeneracion(null);
    setProgreso("Preparando...");
    setGenerando(true);
    try {
      const nuevo = await generarMenuSemanal(usuario.id, setProgreso);
      setMenu(nuevo);
      if (!nuevo) setErrorGeneracion("El menú se generó pero no pudimos leerlo. Intenta recargar.");
    } catch (e) {
      console.warn("generarMenuSemanal:", e.message);
      setErrorGeneracion(
        e.mensaje ?? "No pudimos generar tu menú. Revisa tu conexión y que el backend esté encendido."
      );
    } finally {
      setGenerando(false);
    }
  }

  const cargar = useCallback(async () => {
    if (!usuario?.id) return;
    setCargando(true);
    setError(null);
    try {
      setMenu(await getMenuSemanal(usuario.id));
    } catch (e) {
      console.warn("getMenuSemanal:", e.message);
      setError("No pudimos cargar tu menú. Revisa tu conexión e intenta de nuevo.");
    } finally {
      setCargando(false);
    }
  }, [usuario?.id]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  if (generando) {
    return (
      <View style={styles.centrado}>
        <ActivityIndicator color={colors.primary} size="large" />
        <Text style={[typography.h2, styles.textoCentrado, { marginTop: spacing.md }]}>
          Generando tu menú
        </Text>
        <Text style={[typography.bodyMuted, styles.textoCentrado, { marginTop: spacing.xs }]}>{progreso}</Text>
      </View>
    );
  }

  if (cargando) {
    return (
      <View style={styles.centrado}>
        <ActivityIndicator color={colors.primary} size="large" />
        <Text style={[typography.bodyMuted, { marginTop: spacing.sm }]}>Cargando tu menú...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.centrado}>
        <Text style={[typography.body, styles.textoCentrado]}>{error}</Text>
        <TouchableOpacity style={styles.boton} onPress={cargar}>
          <Text style={styles.botonTexto}>Reintentar</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (!menu) {
    return (
      <View style={styles.centrado}>
        <Text style={[typography.h2, styles.textoCentrado]}>Aún no tienes un menú</Text>
        <Text style={[typography.bodyMuted, styles.textoCentrado, { marginTop: spacing.xs }]}>
          Genera uno con desayuno, almuerzo y cena para cada día de la semana.
        </Text>
        {!!errorGeneracion && (
          <Text style={[typography.body, styles.textoCentrado, styles.errorTexto]}>{errorGeneracion}</Text>
        )}
        <TouchableOpacity style={styles.boton} onPress={generar}>
          <Text style={styles.botonTexto}>Generar mi menú semanal</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <Text style={typography.h1}>Menú de esta semana</Text>
      <Text style={[typography.bodyMuted, { marginBottom: spacing.lg }]}>
        Semana del {formatoSemana(menu.semanaInicio)}. Toca un día para ver su desayuno, almuerzo y cena.
      </Text>

      {!!errorGeneracion && (
        <Text style={[typography.body, styles.errorTexto, { marginBottom: spacing.md }]}>{errorGeneracion}</Text>
      )}

      {menu.dias.map((item) => {
        const n = Object.keys(item.comidas).length;
        return (
          <TouchableOpacity
            key={item.dia}
            activeOpacity={0.7}
            onPress={() => navigation.navigate("DiaMenu", { dia: item })}
          >
            <Card style={styles.filaMenu}>
              <View style={styles.diaBadge}>
                <Text style={styles.diaBadgeTexto}>{item.dia.slice(0, 3).toUpperCase()}</Text>
              </View>
              <View style={{ flex: 1 }}>
                <Text style={typography.h2}>{item.dia}</Text>
                <Text style={typography.bodyMuted}>
                  {n === 0 ? "Sin comidas" : `${n} ${n === 1 ? "comida" : "comidas"}`}
                </Text>
              </View>
              <Text style={styles.flecha}>›</Text>
            </Card>
          </TouchableOpacity>
        );
      })}

      {confirmando ? (
        <Card>
          <Text style={typography.h2}>¿Generar un menú nuevo?</Text>
          <Text style={[typography.bodyMuted, { marginTop: spacing.xs }]}>
            Reemplazará tu menú actual por uno nuevo para toda la semana.
          </Text>
          <View style={styles.filaBotones}>
            <TouchableOpacity style={[styles.botonSecundario, { marginRight: spacing.sm }]} onPress={() => setConfirmando(false)}>
              <Text style={styles.botonSecundarioTexto}>Cancelar</Text>
            </TouchableOpacity>
            <TouchableOpacity style={[styles.boton, styles.botonEnFila]} onPress={generar}>
              <Text style={styles.botonTexto}>Sí, generar</Text>
            </TouchableOpacity>
          </View>
        </Card>
      ) : (
        <TouchableOpacity style={styles.botonSecundario} onPress={() => setConfirmando(true)}>
          <Text style={styles.botonSecundarioTexto}>Generar un menú nuevo</Text>
        </TouchableOpacity>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: spacing.xl },
  centrado: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.background,
    paddingHorizontal: spacing.lg,
  },
  textoCentrado: { textAlign: "center" },
  boton: {
    backgroundColor: colors.primary,
    borderRadius: radius.md,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.lg,
    marginTop: spacing.md,
  },
  botonTexto: { color: colors.white, fontWeight: "700", fontSize: 14 },
  botonEnFila: { marginTop: 0 },
  botonSecundario: {
    borderWidth: 1,
    borderColor: colors.primary,
    borderRadius: radius.md,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.lg,
    alignItems: "center",
  },
  botonSecundarioTexto: { color: colors.primary, fontWeight: "700", fontSize: 14 },
  filaBotones: { flexDirection: "row", marginTop: spacing.md },
  errorTexto: { color: colors.warning, textAlign: "center", marginTop: spacing.md },
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
  flecha: { fontSize: 26, color: colors.textMuted, marginLeft: spacing.sm },
});
