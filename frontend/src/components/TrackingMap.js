import React, { useEffect, useRef, useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import MapView, { Marker } from "react-native-maps";
import { colors, radius, spacing, typography } from "../theme/theme";

const BOGOTA = { latitude: 4.711, longitude: -74.0721 };

function horaUbicacion(location) {
  const fecha = location?.ts ? new Date(location.ts * 1000) : location?.updated_at ? new Date(location.updated_at) : null;
  return fecha && !Number.isNaN(fecha.getTime()) ? ` · ${fecha.toLocaleTimeString()}` : "";
}

export default function TrackingMap({ location, courierOnline }) {
  const [sinMapa, setSinMapa] = useState(false);
  const listoRef = useRef(false);

  useEffect(() => {
    const timer = setTimeout(() => { if (!listoRef.current) setSinMapa(true); }, 6000);
    return () => clearTimeout(timer);
  }, []);

  const lat = Number(location?.lat);
  const lng = Number(location?.lng);
  const tieneUbicacion = Number.isFinite(lat) && Number.isFinite(lng);
  const coordinate = tieneUbicacion ? { latitude: lat, longitude: lng } : BOGOTA;
  const region = { ...coordinate, latitudeDelta: 0.02, longitudeDelta: 0.02 };
  const estado = `${courierOnline ? "Repartidor conectado" : "Repartidor no conectado"}${horaUbicacion(location)}`;
  const coords = tieneUbicacion ? `${lat.toFixed(5)}, ${lng.toFixed(5)}` : "sin datos";

  if (sinMapa) {
    return (
      <View style={styles.mapWrap}>
        <View style={styles.fallback}>
          <Text style={typography.body}>Mapa nativo no disponible en este dispositivo.</Text>
          <Text style={[typography.bodyMuted, { marginTop: spacing.xs }]}>Última ubicación: {coords}</Text>
          <Text style={[typography.bodyMuted, { marginTop: spacing.xs }]}>{estado}</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.mapWrap}>
      <MapView
        style={styles.map}
        initialRegion={region}
        region={region}
        onMapReady={() => { listoRef.current = true; }}
      >
        {tieneUbicacion && <Marker coordinate={coordinate} title="Repartidor" />}
      </MapView>
      <Text style={[typography.bodyMuted, { marginTop: spacing.xs }]}>{estado}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  mapWrap: { marginVertical: spacing.sm },
  map: { height: 260, borderRadius: radius.md, overflow: "hidden" },
  fallback: { backgroundColor: colors.surface, padding: spacing.md, borderRadius: radius.md, minHeight: 120, justifyContent: "center" },
});
