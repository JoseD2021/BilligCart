import React, { useCallback, useEffect, useRef, useState } from "react";
import { useFocusEffect } from "@react-navigation/native";
import { ActivityIndicator, ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import Card from "../components/Card";
import PaymentPanel from "../components/PaymentPanel";
import TrackingMap from "../components/TrackingMap";
import { colors, radius, spacing, typography } from "../theme/theme";
import { api, WS_BASE_URL, getAuthToken } from "../services/api";

const ESTADOS = [
  { clave: "pendiente", etiqueta: "Pendiente" },
  { clave: "confirmado", etiqueta: "Confirmado" },
  { clave: "en_camino", etiqueta: "En camino" },
  { clave: "entregado", etiqueta: "Entregado" },
];

export default function PedidoScreen({ route }) {
  const pedidoId = route.params?.pedidoId;
  const [pedido, setPedido] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);
  const [tracking, setTracking] = useState(false);
  const [location, setLocation] = useState(null);
  const [courierOnline, setCourierOnline] = useState(false);
  const wsRef = useRef(null);

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

  useEffect(() => () => { wsRef.current?.close(); }, []);
  useEffect(() => {
    if (!tracking || !pedido?.id) return;
    const token = getAuthToken();
    const ws = new WebSocket(`${WS_BASE_URL}/ws/tracking/${pedido.id}`);
    wsRef.current = ws;
    ws.onopen = () => ws.send(JSON.stringify({ type: "auth", token }));
    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        if (msg.type === "location") setLocation(msg);
        if (msg.type === "courier_status") setCourierOnline(!!msg.online);
      } catch {}
    };
    ws.onerror = () => setCourierOnline(false);
    return () => { ws.close(); if (wsRef.current === ws) wsRef.current = null; };
  }, [tracking, pedido?.id]);

  if (cargando) return <View style={styles.centrado}><ActivityIndicator color={colors.primary} size="large" /></View>;
  if (error || !pedido) return (
    <View style={styles.centrado}>
      <Text style={typography.body}>{error ?? "Aún no tienes pedidos. Confirma tu lista de compras para crear uno."}</Text>
      <TouchableOpacity onPress={cargar}><Text style={styles.textoActivo}>Actualizar</Text></TouchableOpacity>
    </View>
  );

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <Text style={typography.h1}>Tu pedido</Text>
      <Text style={[typography.bodyMuted, { marginBottom: spacing.md }]}>
        {pedido.repartidor ? `Repartidor: ${pedido.repartidor}` : "Repartidor pendiente de asignación"}
      </Text>
      <Card>
        {ESTADOS.map(({ clave, etiqueta }, i) => {
          const actual = ESTADOS.findIndex(({ clave: c }) => c === pedido.estado);
          const completada = i <= (actual < 0 ? 0 : actual);
          return (
            <View key={clave} style={styles.paso}>
              <View style={[styles.punto, completada && styles.puntoActivo]} />
              <Text style={[typography.body, completada && styles.textoActivo]}>{etiqueta}</Text>
            </View>
          );
        })}
      </Card>
      <TouchableOpacity style={styles.btn} onPress={() => setTracking((v) => !v)}>
        <Text style={styles.btnText}>{tracking ? "Ocultar mapa" : "Ver mapa en vivo"}</Text>
      </TouchableOpacity>
      {tracking && <TrackingMap location={location || pedido.ubicacion} courierOnline={courierOnline} />}
      <Text style={typography.bodyMuted}>Referencia: {pedido.id}</Text>
      <PaymentPanel orderId={pedido.id} />
      <TouchableOpacity onPress={cargar}><Text style={styles.textoActivo}>Actualizar estado</Text></TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingBottom: spacing.xl },
  centrado: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.background, padding: spacing.lg },
  paso: { flexDirection: "row", alignItems: "center", paddingVertical: spacing.sm },
  punto: { width: 14, height: 14, borderRadius: 7, backgroundColor: colors.border, marginRight: spacing.md },
  puntoActivo: { backgroundColor: colors.primary },
  textoActivo: { fontWeight: "700", color: colors.primary },
  btn: { backgroundColor: colors.primary, padding: spacing.sm, borderRadius: radius.md, alignItems: "center", marginVertical: spacing.sm },
  btnText: { color: "#fff", fontWeight: "700" },
});
