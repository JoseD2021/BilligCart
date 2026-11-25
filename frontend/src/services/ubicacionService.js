const NOMINATIM_URL = "https://nominatim.openstreetmap.org/search";

export function esCoordValida(lat, lng) {
  return lat != null && lng != null && Number.isFinite(Number(lat)) && Number.isFinite(Number(lng));
}

export function estadoUbicacion({ lat, lng, buscando, sinResultado }) {
  if (buscando) return "Buscando la dirección en el mapa...";
  if (sinResultado) return "No encontramos esa dirección en el mapa. Puedes continuar con el texto escrito.";
  if (esCoordValida(lat, lng)) return `Ubicación: ${Number(lat).toFixed(5)}, ${Number(lng).toFixed(5)}`;
  return "Escribe una dirección para verla en el mapa.";
}

export async function buscarCoordenadas(direccion, signal) {
  const url = `${NOMINATIM_URL}?format=jsonv2&limit=1&countrycodes=co&q=${encodeURIComponent(direccion)}`;
  const respuesta = await fetch(url, { signal, headers: { Accept: "application/json" } });
  if (!respuesta.ok) throw new Error("No se pudo consultar la dirección.");
  const resultados = await respuesta.json();
  const lat = Number(resultados?.[0]?.lat);
  const lng = Number(resultados?.[0]?.lon);
  return Number.isFinite(lat) && Number.isFinite(lng) ? { lat, lng } : null;
}
