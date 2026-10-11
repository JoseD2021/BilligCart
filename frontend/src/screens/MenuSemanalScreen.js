import React, { useCallback, useEffect, useState } from "react";
import { View, Text, ScrollView, TouchableOpacity, StyleSheet, ActivityIndicator } from "react-native";
import Card from "../components/Card";
import { colors, spacing, radius, typography } from "../theme/theme";
import { useAuth } from "../context/AuthContext";
import { getMenuSemanal, crearMenuDemo } from "../services/menuService";

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

  // Solo desarrollo: genera un menú de ejemplo en el backend para poder probar la pantalla.
  async function generarDemo() {
    setGenerando(true);
    setError(null);
    try {
      setMenu(await crearMenuDemo(usuario.id));
    } catch (e) {
      console.warn("crearMenuDemo:", e.message);
      setError("No pudimos generar el menú de ejemplo. ¿Ya ejecutaste supabase_menu.sql en Supabase?");
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
      setError("No pudimos cargar tu menú. Revisa tu conexión y que supabase_menu.sql esté ejecutado.");
    } finally {
      setCargando(false);
    }
  }, [usuario?.id]);

  useEffect(() => {
    cargar();
  }, [cargar]);

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
          Cuando se genere el de esta semana aparecerá aquí.
        </Text>
        {__DEV__ && (
          <TouchableOpacity style={styles.boton} onPress={generarDemo} disabled={generando}>
            {generando ? (
              <ActivityIndicator color={colors.white} />
            ) : (
              <Text style={styles.botonTexto}>Generar menú de ejemplo</Text>
            )}
          </TouchableOpacity>
        )}
      </View>
    );
  }

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <Text style={typography.h1}>Menú de esta semana</Text>
      <Text style={[typography.bodyMuted, { marginBottom: spacing.lg }]}>
        Semana del {formatoSemana(menu.semanaInicio)}. Toca un día para ver su desayuno, almuerzo y cena.
      </Text>

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
