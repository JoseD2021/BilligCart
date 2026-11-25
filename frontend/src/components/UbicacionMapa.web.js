import React, { useEffect, useRef } from "react";
import { Text, View } from "react-native";
import { spacing, typography } from "../theme/theme";
import { esCoordValida, estadoUbicacion } from "../services/ubicacionService";

const BOGOTA = [4.711, -74.0721];
let leafletPromise = null;

function cargarLeaflet() {
  if (window.L) return Promise.resolve(window.L);
  if (!leafletPromise) {
    leafletPromise = new Promise((resolve, reject) => {
      const css = document.createElement("link");
      css.rel = "stylesheet";
      css.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
      document.head.appendChild(css);
      const script = document.createElement("script");
      script.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
      script.onload = resolve;
      script.onerror = reject;
      document.body.appendChild(script);
    }).catch((error) => {
      leafletPromise = null;
      throw error;
    });
  }
  return leafletPromise;
}

export default function UbicacionMapa({ lat, lng, direccion, buscando, sinResultado }) {
  const ref = useRef(null);
  const mapRef = useRef(null);
  const markerRef = useRef(null);
  const tieneUbicacion = esCoordValida(lat, lng);
  const estado = estadoUbicacion({ lat, lng, buscando, sinResultado });

  useEffect(() => {
    if (!ref.current) return undefined;
    let cancelled = false;
    cargarLeaflet()
      .then(() => {
        if (cancelled || !ref.current || !window.L) return;
        if (!mapRef.current) {
          mapRef.current = window.L.map(ref.current).setView(BOGOTA, 12);
          window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            attribution: "&copy; OpenStreetMap",
          }).addTo(mapRef.current);
        }
        if (tieneUbicacion) {
          const pos = [Number(lat), Number(lng)];
          if (!markerRef.current) markerRef.current = window.L.marker(pos).addTo(mapRef.current);
          else markerRef.current.setLatLng(pos);
          if (direccion) markerRef.current.bindPopup(direccion);
          mapRef.current.setView(pos, Math.max(mapRef.current.getZoom() || 0, 14));
        } else if (markerRef.current) {
          mapRef.current.removeLayer(markerRef.current);
          markerRef.current = null;
          mapRef.current.setView(BOGOTA, 12);
        }
        mapRef.current.invalidateSize();
      })
      .catch((error) => { console.warn("[mapa] no se pudo inicializar Leaflet", error); });
    return () => { cancelled = true; };
  }, [lat, lng, direccion, tieneUbicacion]);

  useEffect(() => () => {
    mapRef.current?.remove();
    mapRef.current = null;
    markerRef.current = null;
  }, []);

  return (
    <View style={{ marginBottom: spacing.md }}>
      <div ref={ref} style={{ height: 180, width: "100%", borderRadius: 14 }} />
      <Text style={[typography.bodyMuted, { marginTop: spacing.xs }]}>{estado}</Text>
    </View>
  );
}
