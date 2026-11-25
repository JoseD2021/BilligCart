import React, { useEffect, useRef, useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import MapView, { Marker } from "react-native-maps";
import { colors, radius, spacing, typography } from "../theme/theme";
import { esCoordValida, estadoUbicacion } from "../services/ubicacionService";

const BOGOTA = { latitude: 4.711, longitude: -74.0721 };

export default function UbicacionMapa({ lat, lng, direccion, buscando, sinResultado }) {
  const [sinMapa, setSinMapa] = useState(false);
  const listoRef = useRef(false);

  useEffect(() => {
    const timer = setTimeout(() => { if (!listoRef.current) setSinMapa(true); }, 6000);
    return () => clearTimeout(timer);
  }, []);

  const tieneUbicacion = esCoordValida(lat, lng);
  const coordinate = tieneUbicacion
    ? { latitude: Number(lat), longitude: Number(lng) }
    : BOGOTA;
  const region = { ...coordinate, latitudeDelta: 0.02, longitudeDelta: 0.02 };
  const estado = estadoUbicacion({ lat, lng, buscando, sinResultado });

  if (sinMapa) {
    return (
      <View style={styles.mapWrap}>
        <View style={styles.fallback}>
          <Text style={typography.body}>{estado}</Text>
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
        {tieneUbicacion && <Marker coordinate={coordinate} title={direccion || "Dirección de entrega"} />}
      </MapView>
      <Text style={[typography.bodyMuted, { marginTop: spacing.xs }]}>{estado}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  mapWrap: { marginBottom: spacing.md },
  map: { height: 180, borderRadius: radius.md, overflow: "hidden" },
  fallback: {
    backgroundColor: colors.surface,
    padding: spacing.md,
    borderRadius: radius.md,
    minHeight: 120,
    justifyContent: "center",
  },
});
