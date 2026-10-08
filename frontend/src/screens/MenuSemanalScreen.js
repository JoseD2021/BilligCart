import React, { useEffect, useState } from "react";
import { View, Text, ScrollView, TouchableOpacity, StyleSheet, ActivityIndicator } from "react-native";
import Card from "../components/Card";
import { colors, spacing, typography } from "../theme/theme";
import { api } from "../services/api";
import { useAuth } from "../context/AuthContext";

// Forma esperada de cada día que devuelve el backend:
// { dia: "Lunes", comidas: { desayuno: {nombre, calorias}, almuerzo: {...}, cena: {...} } }

// Datos de ejemplo mientras el backend no está disponible.
const MENU_DEMO = [
  { dia: "Lunes", comidas: {
    desayuno: { nombre: "Huevos revueltos con pan", calorias: 350 },
    almuerzo: { nombre: "Lentejas con arroz", calorias: 620 },
    cena: { nombre: "Sopa de verduras", calorias: 300 } } },
  { dia: "Martes", comidas: {
    desayuno: { nombre: "Arepa con queso", calorias: 380 },
    almuerzo: { nombre: "Pollo al horno con papa", calorias: 650 },
    cena: { nombre: "Ensalada de atún", calorias: 320 } } },
  { dia: "Miércoles", comidas: {
    desayuno: { nombre: "Avena con frutas", calorias: 330 },
    almuerzo: { nombre: "Ensalada de garbanzos", calorias: 540 },
    cena: { nombre: "Crema de tomate", calorias: 280 } } },
  { dia: "Jueves", comidas: {
    desayuno: { nombre: "Pan con huevo", calorias: 360 },
    almuerzo: { nombre: "Pasta integral con verduras", calorias: 600 },
    cena: { nombre: "Tortilla de espinaca", calorias: 310 } } },
  { dia: "Viernes", comidas: {
    desayuno: { nombre: "Yogur con granola", calorias: 340 },
    almuerzo: { nombre: "Arroz con pollo", calorias: 640 },
    cena: { nombre: "Sopa de lentejas", calorias: 330 } } },
  { dia: "Sábado", comidas: {
    desayuno: { nombre: "Calentado con huevo", calorias: 420 },
    almuerzo: { nombre: "Tacos de frijol", calorias: 580 },
    cena: { nombre: "Pizza casera de vegetales", calorias: 450 } } },
  { dia: "Domingo", comidas: {
    desayuno: { nombre: "Pancakes de avena", calorias: 400 },
    almuerzo: { nombre: "Sancocho ligero", calorias: 620 },
    cena: { nombre: "Arroz con vegetales", calorias: 380 } } },
];

function totalCalorias(comidas) {
  return Object.values(comidas).reduce((suma, c) => suma + (c.calorias || 0), 0);
}

export default function MenuSemanalScreen({ navigation }) {
  const { usuario } = useAuth();
  const usuarioId = usuario?.id || "demo";
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
        Toca un día para ver su desayuno, almuerzo y cena.
      </Text>

      {menu.map((item) => (
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
                3 comidas · {totalCalorias(item.comidas)} kcal aprox.
              </Text>
            </View>
            <Text style={styles.flecha}>›</Text>
          </Card>
        </TouchableOpacity>
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
  flecha: { fontSize: 26, color: colors.textMuted, marginLeft: spacing.sm },
});
