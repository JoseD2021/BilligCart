import React, { useEffect, useState } from "react";
import { View, Text, StyleSheet, ActivityIndicator } from "react-native";
import Card from "../components/Card";
import { colors, spacing, radius, typography } from "../theme/theme";
import { api } from "../services/api";

const ETAPAS = ["Confirmado", "Preparando", "En camino", "Entregado"];

const PEDIDO_DEMO = { etapa: 2, repartidor: "Camilo R.", tiempoEstimado: "18 min" };

export default function PedidoScreen({ pedidoId = "demo" }) {
  const [pedido, setPedido] = useState(null);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    api
      .getEstadoPedido(pedidoId)
      .then(setPedido)
      .catch(() => setPedido(PEDIDO_DEMO))
      .finally(() => setCargando(false));
  }, [pedidoId]);

  if (cargando) {
    return (
      <View style={styles.centrado}>
        <ActivityIndicator color={colors.primary} size="large" />
      </View>
    );
  }

  return (
    <View style={styles.screen}>
      <Text style={typography.h1}>Tu pedido</Text>
      <Text style={[typography.bodyMuted, { marginBottom: spacing.lg }]}>
        Repartidor: {pedido.repartidor} · Llega en {pedido.tiempoEstimado}
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
