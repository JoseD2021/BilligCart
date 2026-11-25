import React, { useEffect, useRef } from "react";
import { Text, View } from "react-native";
import { spacing, typography } from "../theme/theme";

function horaUbicacion(location) {
  const fecha = location?.ts ? new Date(location.ts * 1000) : location?.updated_at ? new Date(location.updated_at) : null;
  return fecha && !Number.isNaN(fecha.getTime()) ? ` · ${fecha.toLocaleTimeString()}` : "";
}

export default function TrackingMap({ location, courierOnline }) {
  const ref = useRef(null);
  const mapRef = useRef(null);
  const markerRef = useRef(null);

  useEffect(() => {
    if (!ref.current) return;
    let cancelled = false;
    async function ensure() {
      if (!window.L) {
        await new Promise((resolve, reject) => {
          const css = document.createElement("link");
          css.rel = "stylesheet"; css.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"; document.head.appendChild(css);
          const s = document.createElement("script");
          s.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"; s.onload = resolve; s.onerror = reject; document.body.appendChild(s);
        });
      }
      if (cancelled || !ref.current) return;
      if (!mapRef.current) {
        mapRef.current = window.L.map(ref.current).setView([4.711, -74.0721], 13);
        window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { attribution: "&copy; OpenStreetMap" }).addTo(mapRef.current);
      }
      const lat = Number(location?.lat);
      const lng = Number(location?.lng);
      if (Number.isFinite(lat) && Number.isFinite(lng)) {
        const pos = [lat, lng];
        if (!markerRef.current) markerRef.current = window.L.marker(pos).addTo(mapRef.current);
        else markerRef.current.setLatLng(pos);
        mapRef.current.invalidateSize();
        mapRef.current.setView(pos, mapRef.current.getZoom() || 15);
      }
    }
    ensure().catch((error) => { console.warn("[mapa] no se pudo inicializar Leaflet", error); });
    return () => { cancelled = true; };
  }, [location]);

  return (
    <View style={{ marginVertical: spacing.sm }}>
      <div ref={ref} style={{ height: 260, width: "100%", borderRadius: 12 }} />
      <Text style={[typography.bodyMuted, { marginTop: spacing.xs }]}>
        {courierOnline ? "Repartidor conectado" : "Repartidor no conectado"}{horaUbicacion(location)}
      </Text>
    </View>
  );
}
