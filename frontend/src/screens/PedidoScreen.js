import React, { useCallback, useState } from "react";
import { useFocusEffect } from "@react-navigation/native";
import { View, Text, StyleSheet, ActivityIndicator, TouchableOpacity } from "react-native";
import Card from "../components/Card";
import { colors, spacing, radius, typography } from "../theme/theme";
import { api } from "../services/api";

const ETAPAS = ["Confirmado", "Preparando", "En camino", "Entregado"];

export default function PedidoScreen({ route }) {
  const pedidoId = route.params?.pedidoId;
  const [pedido, setPedido] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);

  const cargar = useCallback(() => {
    let active = true;
    setCargando(true);
    setError(null);
    const request = pedidoId ? api.getEstadoPedido(pedidoId) : api.getPedidoActual();
    request.then((data) => { if (active) setPedido(data); })
      .catch((e) => { if (active) setError(e.message); })
      .finally(() => { if (active) setCargando(false); });
    return () => { active = false; };
  }, [pedidoId]);
  useFocusEffect(cargar);

  if (cargando) {
    return (
      <View style={styles.centrado}>
        <ActivityIndicator color={colors.primary} size="large" />
      </View>
    );
  }

  if (error || !pedido) {
    return (
      <View style={styles.centrado}>
        <Text style={typography.body}>{error ?? "Aún no tienes pedidos. Confirma tu lista de compras para crear uno."}</Text>
        <TouchableOpacity onPress={cargar}><Text style={styles.textoActivo}>Actualizar</Text></TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.screen}>
      <Text style={typography.h1}>Tu pedido</Text>
      <Text style={[typography.bodyMuted, { marginBottom: spacing.lg }]}>
        {pedido.repartidor ? `Repartidor: ${pedido.repartidor}` : "Repartidor pendiente de asignación"}
        {pedido.tiempo_estimado ? ` · Llega en ${pedido.tiempo_estimado}` : ""}
      </Text>

      <Card>
        {ETAPAS.map((etapa, i) => {
          const completada = i <= pedido.etapa;
          return (
            <View key={etapa} style={styles.paso}>
              <View style={[styles.punto, completada && styles.puntoActivo]} />
              <Text style={[typography.body, completada && styles.textoActivo]}>{etapa}</Text>
            </View>
          );
        })}
      </Card>
      <Text style={typography.bodyMuted}>Referencia: {pedido.id}</Text>
      <TouchableOpacity onPress={cargar}><Text style={styles.textoActivo}>Actualizar estado</Text></TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background, padding: spacing.lg },
  centrado: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.background },
  paso: { flexDirection: "row", alignItems: "center", paddingVertical: spacing.sm },
  punto: {
    width: 14,
    height: 14,
    borderRadius: 7,
    backgroundColor: colors.border,
    marginRight: spacing.md,
  },
  puntoActivo: { backgroundColor: colors.primary },
  textoActivo: { fontWeight: "700", color: colors.primary },
});
