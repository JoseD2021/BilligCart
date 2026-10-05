
export const colors = {
  primary: "#2F6F4E",      // acciones principales, encabezados
  primaryDark: "#1F4D36",
  accent: "#E3A008",       // precios, ahorro, destacados
  warning: "#E8604C",      // alertas de presupuesto excedido
  background: "#FAF7F2",   // fondo general
  surface: "#FFFFFF",
  border: "#E7E1D6",
  text: "#26302A",
  textMuted: "#6B7368",
  white: "#FFFFFF",
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
};

export const radius = {
  sm: 8,
  md: 14,
  lg: 22,
  pill: 999,
};

export const typography = {
  h1: { fontSize: 26, fontWeight: "700", color: colors.text },
  h2: { fontSize: 19, fontWeight: "700", color: colors.text },
  body: { fontSize: 15, fontWeight: "400", color: colors.text },
  bodyMuted: { fontSize: 14, fontWeight: "400", color: colors.textMuted },
  label: { fontSize: 12, fontWeight: "600", color: colors.textMuted },
  price: { fontSize: 16, fontWeight: "700", color: colors.accent },
};
