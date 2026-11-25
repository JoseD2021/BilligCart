import React, { useCallback, useRef, useState } from "react";
import { useFocusEffect } from "@react-navigation/native";
import {
  ActivityIndicator,
  FlatList,
  RefreshControl,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { colors, radius, spacing, typography } from "../theme/theme";
import { api } from "../services/api";

const ESTADOS = {
  pendiente: "Pendiente",
  confirmado: "Confirmado",
  en_camino: "En camino",
  entregado: "Entregado",
};

function formatearFecha(value) {
  if (!value) return "Fecha no disponible";
  const fecha = new Date(value);
  if (Number.isNaN(fecha.getTime())) return "Fecha no disponible";
  return fecha.toLocaleString("es-CO", {
    day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

function formatearTotal(value) {
  const numero = Number(value);
  return Number.isFinite(numero) ? `$${numero.toLocaleString("es-CO")}` : "$0";
}

export default function PedidosScreen({ navigation, route }) {
  const pedidoRecienCreado = route.params?.pedidoId;
  const [pedidos, setPedidos] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);
  // Evita volver a abrir el detalle automáticamente al regresar desde él.
  const detalleYaAbierto = useRef(false);

  const cargar = useCallback(() => {
    let active = true;
    setCargando(true);
    setError(null);

    api.getPedidos()
      .then((data) => {
        if (!active) return;
        const lista = Array.isArray(data) ? data : [];
        setPedidos(lista);
        // Con un solo pedido se conserva el comportamiento anterior: entrar directo al detalle.
        if (lista.length === 1 && !detalleYaAbierto.current) {
          detalleYaAbierto.current = true;
          navigation.navigate("PedidoDetalle", { pedidoId: lista[0].id });
        }
      })
      .catch((e) => { if (active) setError(e.message); })
      .finally(() => { if (active) setCargando(false); });

    return () => { active = false; };
  }, [navigation]);

  useFocusEffect(cargar);

  const abrirDetalle = useCallback((pedidoId) => {
    detalleYaAbierto.current = true;
    navigation.navigate("PedidoDetalle", { pedidoId });
  }, [navigation]);

  const renderItem = ({ item }) => {
    const destacado = item.id === pedidoRecienCreado;
    return (
      <TouchableOpacity
        style={[styles.card, destacado && styles.cardDestacada]}
        onPress={() => abrirDetalle(item.id)}
        accessibilityRole="button"
      >
        <View style={styles.cardHeader}>
          <Text style={typography.h2}>Pedido #{String(item.id).slice(0, 8)}</Text>
          <Text style={styles.chevron}>›</Text>
        </View>
        <Text style={[styles.estado, item.estado === "entregado" && styles.estadoEntregado]}>
          {ESTADOS[item.estado] ?? item.estado}
        </Text>
        <Text style={typography.bodyMuted}>{formatearFecha(item.created_at)}</Text>
        <View style={styles.cardFooter}>
          <Text style={typography.price}>{formatearTotal(item.total)}</Text>
          <Text style={typography.bodyMuted}>{item.items?.length ?? 0} productos</Text>
        </View>
        {item.repartidor_email ? (
          <Text style={[typography.bodyMuted, styles.repartidor]}>Repartidor: {item.repartidor_email}</Text>
        ) : null}
        {destacado ? <Text style={styles.nuevo}>Pedido recién creado</Text> : null}
      </TouchableOpacity>
    );
  };

  if (cargando && !pedidos.length) {
    return <View style={styles.centrado}><ActivityIndicator color={colors.primary} size="large" /></View>;
  }

  if (error && !pedidos.length) {
    return (
      <View style={styles.centrado}>
        <Text style={typography.body}>{error}</Text>
        <TouchableOpacity onPress={cargar}>
          <Text style={styles.textoActivo}>Reintentar</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.screen}>
      <FlatList
        data={pedidos}
        keyExtractor={(item) => item.id}
        renderItem={renderItem}
        contentContainerStyle={styles.content}
        ListHeaderComponent={(
          <>
            <Text style={typography.h1}>Tus pedidos</Text>
            <Text style={[typography.bodyMuted, styles.subtitulo]}>
              {pedidos.length > 1
                ? "Elige un pedido para ver su estado y sus detalles."
                : "Este es tu pedido actual."}
            </Text>
          </>
        )}
        ListEmptyComponent={(
          <View style={styles.vacio}>
            <Text style={typography.body}>Aún no tienes pedidos. Confirma tu lista de compras para crear uno.</Text>
            <TouchableOpacity onPress={cargar}>
              <Text style={styles.textoActivo}>Actualizar</Text>
            </TouchableOpacity>
          </View>
        )}
        refreshControl={<RefreshControl refreshing={cargando} onRefresh={cargar} colors={[colors.primary]} />}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: spacing.xl },
  subtitulo: { marginTop: spacing.xs, marginBottom: spacing.lg },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  cardDestacada: { borderColor: colors.primary, borderWidth: 2 },
  cardHeader: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  chevron: { fontSize: 26, lineHeight: 26, color: colors.primary },
  estado: {
    alignSelf: "flex-start",
    marginTop: spacing.sm,
    marginBottom: spacing.xs,
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    borderRadius: radius.pill,
    backgroundColor: colors.background,
    color: colors.primary,
    fontSize: 12,
    fontWeight: "700",
    overflow: "hidden",
  },
  estadoEntregado: { color: colors.textMuted },
  cardFooter: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: spacing.sm },
  repartidor: { marginTop: spacing.xs },
  nuevo: { marginTop: spacing.sm, color: colors.primary, fontSize: 12, fontWeight: "700" },
  centrado: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.background, padding: spacing.lg },
  vacio: { alignItems: "center", paddingTop: spacing.xl },
  textoActivo: { fontWeight: "700", color: colors.primary, marginTop: spacing.md },
});
