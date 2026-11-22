import React, { useCallback, useEffect, useRef, useState } from "react";
import { ActivityIndicator, Alert, FlatList, Platform, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { api, WS_BASE_URL, getAuthToken } from "../services/api";
import { colors, radius, spacing, typography } from "../theme/theme";

const ESTADOS = ["confirmado", "en_camino", "entregado"];

export default function RepartidorScreen() {
  const [disponibles, setDisponibles] = useState([]);
  const [asignados, setAsignados] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [activo, setActivo] = useState(null);
  const [modo, setModo] = useState("idle");
  const wsRef = useRef(null);
  const watchRef = useRef(null);

  const cargar = useCallback(async () => {
    setCargando(true);
    try {
      const [d, a] = await Promise.all([api.getPedidosDisponibles(), api.getPedidosAsignados()]);
      setDisponibles(d); setAsignados(a);
      if (!activo && a.length) setActivo(a[0].id);
    } catch (e) { Alert.alert("Error", e.message); }
    finally { setCargando(false); }
  }, [activo]);

  useEffect(() => { cargar(); }, [cargar]);

  useEffect(() => () => {
    wsRef.current?.close();
    if (watchRef.current != null && navigator?.geolocation) navigator.geolocation.clearWatch(watchRef.current);
  }, []);

  useEffect(() => {
    if (!activo) return;
    const token = getAuthToken();
    const ws = new WebSocket(`${WS_BASE_URL}/ws/courier/${activo}`);
    wsRef.current = ws;
    let intervalMs = 10000;
    let timer = null;

    const sendLocation = (pos) => {
      const c = pos?.coords;
      if (!c || ws.readyState !== 1) return;
      ws.send(JSON.stringify({ type: "location", lat: c.latitude, lng: c.longitude, accuracy: c.accuracy, heading: c.heading, speed: c.speed }));
    };

    const startGeo = () => {
      if (timer) clearInterval(timer);
      if (Platform.OS === "web" && navigator?.geolocation) {
        if (watchRef.current != null) navigator.geolocation.clearWatch(watchRef.current);
        watchRef.current = navigator.geolocation.watchPosition(sendLocation, () => {}, { enableHighAccuracy: true, maximumAge: 5000, timeout: 10000 });
        timer = setInterval(() => navigator.geolocation.getCurrentPosition(sendLocation, () => {}, { enableHighAccuracy: true, maximumAge: 5000, timeout: 10000 }), intervalMs);
      } else {
        Alert.alert("Ubicación", "La demo de GPS está optimizada para web; en móvil requiere configuración de permisos de ubicación.");
      }
    };

    ws.onopen = () => ws.send(JSON.stringify({ type: "auth", token }));
    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        if (msg.type === "start_streaming") {
          intervalMs = msg.interval_ms || intervalMs;
          setModo(msg.mode || "live");
          startGeo();
        }
        if (msg.type === "stop_streaming") { setModo("idle"); }
      } catch {}
    };
    ws.onerror = () => {};
    return () => {
      if (timer) clearInterval(timer);
      if (watchRef.current != null && navigator?.geolocation) navigator.geolocation.clearWatch(watchRef.current);
      ws.close();
      if (wsRef.current === ws) wsRef.current = null;
    };
  }, [activo]);

  async function aceptar(id) {
    try { await api.aceptarPedido(id); setActivo(id); await cargar(); } catch (e) { Alert.alert("No se pudo aceptar", e.message); }
  }
  async function cambiarEstado(id, estado) {
    try { await api.actualizarEstadoPedido(id, estado); await cargar(); } catch (e) { Alert.alert("No se pudo actualizar", e.message); }
  }

  if (cargando) return <View style={styles.centrado}><ActivityIndicator color={colors.primary} size="large" /></View>;

  const Pedido = ({ item, assigned }) => (
    <View style={styles.card}>
      <Text style={typography.h2}>Pedido {String(item.id).slice(0, 8)}</Text>
      <Text style={typography.bodyMuted}>Estado: {item.estado} · Total: ${Number(item.total).toLocaleString("es-CO")}</Text>
      {!assigned ? (
        <TouchableOpacity style={styles.btn} onPress={() => aceptar(item.id)}><Text style={styles.btnText}>Aceptar pedido</Text></TouchableOpacity>
      ) : (
        <View style={styles.row}>
          {ESTADOS.map((e) => (
            <TouchableOpacity key={e} style={[styles.smallBtn, item.estado === e && styles.smallBtnActive]} onPress={() => cambiarEstado(item.id, e)}>
              <Text style={styles.smallBtnText}>{e}</Text>
            </TouchableOpacity>
          ))}
          <TouchableOpacity style={styles.smallBtn} onPress={() => setActivo(item.id)}><Text style={styles.smallBtnText}>{activo === item.id ? `GPS ${modo}` : "Activar GPS"}</Text></TouchableOpacity>
        </View>
      )}
    </View>
  );

  return (
    <View style={styles.screen}>
      <Text style={typography.h1}>Modo repartidor</Text>
      <Text style={[typography.bodyMuted, { marginBottom: spacing.sm }]}>Pedido activo GPS: {activo ? String(activo).slice(0, 8) : "ninguno"} · modo {modo}</Text>
      <Text style={typography.h2}>Disponibles</Text>
      <FlatList data={disponibles} keyExtractor={(i) => String(i.id)} renderItem={({ item }) => <Pedido item={item} />} ListEmptyComponent={<Text style={typography.bodyMuted}>No hay pedidos pendientes.</Text>} />
      <Text style={[typography.h2, { marginTop: spacing.md }]}>Mis pedidos</Text>
      <FlatList data={asignados} keyExtractor={(i) => String(i.id)} renderItem={({ item }) => <Pedido item={item} assigned />} ListEmptyComponent={<Text style={typography.bodyMuted}>No tienes pedidos asignados.</Text>} />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background, padding: spacing.lg },
  centrado: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.background },
  card: { backgroundColor: colors.surface, padding: spacing.md, borderRadius: radius.md, marginVertical: spacing.xs, borderWidth: 1, borderColor: colors.border },
  row: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: spacing.sm },
  btn: { backgroundColor: colors.primary, padding: spacing.sm, borderRadius: radius.sm, marginTop: spacing.sm, alignItems: "center" },
  btnText: { color: "#fff", fontWeight: "700" },
  smallBtn: { backgroundColor: colors.border, paddingVertical: 6, paddingHorizontal: 10, borderRadius: radius.sm },
  smallBtnActive: { backgroundColor: colors.primary },
  smallBtnText: { color: "#111", fontSize: 12, fontWeight: "600" },
});