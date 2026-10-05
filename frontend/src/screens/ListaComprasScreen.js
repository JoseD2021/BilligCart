import React, { useEffect, useState } from "react";
import { View, Text, FlatList, TouchableOpacity, StyleSheet, ActivityIndicator, Alert } from "react-native";
import { colors, spacing, radius, typography } from "../theme/theme";
import { api } from "../services/api";

const LISTA_DEMO = {
  presupuesto: 150000,
  total: 132500,
  items: [
    { id: "1", nombre: "Arroz 1kg", supermercado: "D1", precio: 4200, comprado: false },
    { id: "2", nombre: "Lentejas 500g", supermercado: "Éxito", precio: 5100, comprado: false },
    { id: "3", nombre: "Pechuga de pollo 1kg", supermercado: "Éxito", precio: 15900, comprado: true },
    { id: "4", nombre: "Tomate x kg", supermercado: "D1", precio: 3200, comprado: false },
    { id: "5", nombre: "Pasta integral 500g", supermercado: "Ara", precio: 4800, comprado: false },
  ],
};

export default function ListaComprasScreen({ usuarioId = "demo" }) {
  const [lista, setLista] = useState(null);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    api
      .getListaDeCompras(usuarioId)
      .then(setLista)
      .catch(() => setLista(LISTA_DEMO))
      .finally(() => setCargando(false));
  }, [usuarioId]);

  if (cargando) {
    return (
      <View style={styles.centrado}>
        <ActivityIndicator color={colors.primary} size="large" />
      </View>
    );
  }

  const excedePresupuesto = lista.total > lista.presupuesto;

  async function confirmar() {
    try {
      await api.confirmarCompra(usuarioId);
      Alert.alert("Pedido confirmado", "Un repartidor será asignado en breve.");
    } catch (e) {
      Alert.alert("No se pudo confirmar", "Intenta de nuevo en unos minutos.");
    }
  }

  return (
    <View style={styles.screen}>
      <View style={styles.header}>
        <Text style={typography.h1}>Lista de compras</Text>
        <View style={styles.resumen}>
          <View>
            <Text style={typography.label}>TOTAL ESTIMADO</Text>
            <Text style={[typography.price, excedePresupuesto && { color: colors.warning }]}>
              ${lista.total.toLocaleString("es-CO")}
            </Text>
          </View>
          <View>
            <Text style={typography.label}>PRESUPUESTO</Text>
            <Text style={typography.bodyMuted}>${lista.presupuesto.toLocaleString("es-CO")}</Text>
          </View>
        </View>
        {excedePresupuesto && (
          <View style={styles.avisoPresupuesto}>
            <Text style={styles.avisoTexto}>
              Te pasaste del presupuesto por ${(lista.total - lista.presupuesto).toLocaleString("es-CO")}
            </Text>
          </View>
        )}
      </View>

      <FlatList
        data={lista.items}
        keyExtractor={(item) => item.id}
        contentContainerStyle={{ padding: spacing.lg }}
        renderItem={({ item }) => (
          <View style={styles.fila}>
            <View style={[styles.check, item.comprado && styles.checkActivo]} />
            <View style={{ flex: 1 }}>
              <Text style={[typography.body, item.comprado && styles.tachado]}>{item.nombre}</Text>
              <Text style={typography.bodyMuted}>{item.supermercado}</Text>
            </View>
            <Text style={typography.price}>${item.precio.toLocaleString("es-CO")}</Text>
          </View>
        )}
      />

      <View style={styles.footer}>
        <TouchableOpacity style={styles.botonConfirmar} onPress={confirmar}>
          <Text style={styles.botonConfirmarTexto}>Confirmar y pagar</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  centrado: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.background },
  header: { padding: spacing.lg, paddingBottom: 0 },
  resumen: {
    flexDirection: "row",
    justifyContent: "space-between",
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.md,
    marginTop: spacing.md,
  },
  avisoPresupuesto: {
    backgroundColor: "#FCEAE6",
    borderRadius: radius.sm,
    padding: spacing.sm,
    marginTop: spacing.sm,
  },
  avisoTexto: { color: colors.warning, fontSize: 13, fontWeight: "600" },
  fila: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  check: {
    width: 20,
    height: 20,
    borderRadius: 5,
    borderWidth: 2,
    borderColor: colors.border,
    marginRight: spacing.md,
  },
  checkActivo: { backgroundColor: colors.primary, borderColor: colors.primary },
  tachado: { textDecorationLine: "line-through", color: colors.textMuted },
  footer: { padding: spacing.lg, borderTopWidth: 1, borderTopColor: colors.border },
  botonConfirmar: {
    backgroundColor: colors.accent,
    borderRadius: radius.md,
    paddingVertical: spacing.md,
    alignItems: "center",
  },
  botonConfirmarTexto: { color: colors.white, fontWeight: "700", fontSize: 15 },
});
