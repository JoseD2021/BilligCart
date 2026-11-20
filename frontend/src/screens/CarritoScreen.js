import React, { useCallback, useState } from "react";
import {
  View, Text, FlatList, ScrollView, TouchableOpacity, StyleSheet, ActivityIndicator, Alert,
} from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import Card from "../components/Card";
import PaymentPanel from "../components/PaymentPanel";
import SelectorUbicacion from "../components/SelectorUbicacion";
import { colors, spacing, radius, typography } from "../theme/theme";
import { api } from "../services/api";

const PASOS = ["Productos", "Total", "Pago", "Envío"];
const pesos = (n) => `$${Number(n).toLocaleString("es-CO")}`;

export default function CarritoScreen({ navigation }) {
  const [paso, setPaso] = useState(0);
  const [lista, setLista] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);
  const [pedido, setPedido] = useState(null); // se crea al confirmar (paso Total -> Pago)
  const [confirmando, setConfirmando] = useState(false);
  const [envio, setEnvio] = useState({ direccion: "", referencia: "", lat: null, lng: null });

  // Productos y precios: salen de /compras, que arma la lista con los ingredientes del menú semanal.
  const cargar = useCallback(() => {
    let active = true;
    setCargando(true);
    setError(null);
    api.getListaDeCompras()
      .then((data) => { if (active) setLista(data); })
      .catch((e) => { if (active) setError(e.message); })
      .finally(() => { if (active) setCargando(false); });
    return () => { active = false; };
  }, []);
  useFocusEffect(cargar);

  async function confirmar() {
    if (confirmando) return;
    setConfirmando(true);
    try {
      setPedido(await api.confirmarCompra()); // crea el pedido; Stripe cobra sobre ese pedido
      setPaso(2);
    } catch (e) {
      Alert.alert("No se pudo confirmar", e.message);
    } finally {
      setConfirmando(false);
    }
  }

  function finalizar() {
    if (!envio.direccion.trim() && envio.lat == null) {
      Alert.alert("Falta la dirección", "Escribe la dirección de entrega para continuar.");
      return;
    }
    // TODO: guardar `envio` (direccion, referencia, lat, lng) en el pedido cuando exista el endpoint.
    const pedidoId = pedido.id;
    setPaso(0);
    setPedido(null);
    setEnvio({ direccion: "", referencia: "", lat: null, lng: null });
    navigation.navigate("Pedido", { pedidoId });
  }

  if (cargando && !lista) {
    return <View style={styles.centrado}><ActivityIndicator color={colors.primary} size="large" /></View>;
  }

  if (error || !lista?.items?.length) {
    return (
      <View style={styles.centrado}>
        <Text style={[typography.body, { textAlign: "center", paddingHorizontal: spacing.lg }]}>
          {error ?? "Genera un menú para ver tu lista de compras."}
        </Text>
        <TouchableOpacity onPress={cargar} style={styles.botonSecundario}>
          <Text style={styles.botonSecundarioTexto}>Actualizar</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const excedePresupuesto = lista.presupuesto > 0 && lista.total > lista.presupuesto;

  return (
    <View style={styles.screen}>
      <View style={styles.header}>
        <Text style={typography.h1}>Carrito</Text>
        <View style={styles.stepper}>
          {PASOS.map((nombre, i) => (
            <View key={nombre} style={styles.stepItem}>
              <View style={[styles.stepPunto, i <= paso && styles.stepPuntoActivo]}>
                <Text style={[styles.stepNumero, i <= paso && { color: colors.white }]}>{i + 1}</Text>
              </View>
              <Text style={[styles.stepTexto, i === paso && { color: colors.primary, fontWeight: "700" }]}>{nombre}</Text>
            </View>
          ))}
        </View>
      </View>

      {/* ---------- 1. PRODUCTOS ---------- */}
      {paso === 0 && (
        <>
          <FlatList
            data={lista.items}
            keyExtractor={(item) => item.id}
            contentContainerStyle={{ padding: spacing.lg }}
            renderItem={({ item }) => (
              <View style={styles.fila}>
                <View style={{ flex: 1 }}>
                  <Text style={typography.body}>{item.nombre}</Text>
                  <Text style={typography.bodyMuted}>{item.cantidad} {item.unidad} · {item.supermercado ?? "Sin cotizar"}</Text>
                </View>
                <Text style={typography.price}>{item.precio == null ? "Pendiente" : pesos(item.precio)}</Text>
              </View>
            )}
          />
          <Footer
            etiqueta={`${lista.items.length} productos · ${pesos(lista.total)}`}
            boton="Ver total"
            onPress={() => setPaso(1)}
          />
        </>
      )}

      {/* ---------- 2. TOTAL ---------- */}
      {paso === 1 && (
        <>
          <ScrollView contentContainerStyle={{ padding: spacing.lg }}>
            <Card>
              <Text style={typography.label}>TOTAL DE REFERENCIA</Text>
              <Text style={[typography.price, { fontSize: 28, marginTop: spacing.xs }, excedePresupuesto && { color: colors.warning }]}>
                {pesos(lista.total)}
              </Text>
              <Text style={[typography.bodyMuted, { marginTop: spacing.xs }]}>
                Presupuesto: {lista.presupuesto ? pesos(lista.presupuesto) : "Sin definir"}
              </Text>
              {excedePresupuesto && (
                <View style={styles.avisoPresupuesto}>
                  <Text style={styles.avisoTexto}>Te pasaste del presupuesto por {pesos(lista.total - lista.presupuesto)}</Text>
                </View>
              )}
            </Card>
            <Text style={typography.bodyMuted}>
              Precios de referencia de los productos encontrados. El costo final depende de la presentación y la cantidad comprada.
            </Text>
            {lista.precios_pendientes > 0 && (
              <Text style={styles.avisoTexto}>Faltan precios para {lista.precios_pendientes} ingredientes.</Text>
            )}
          </ScrollView>
          <Footer
            boton={confirmando ? "Confirmando..." : "Confirmar y pagar"}
            deshabilitado={!lista.puede_confirmar || confirmando}
            onPress={confirmar}
            atras={() => setPaso(0)}
          />
        </>
      )}

      {/* ---------- 3. PAGO (Stripe Checkout, el PaymentPanel del proyecto) ---------- */}
      {paso === 2 && pedido && (
        <ScrollView contentContainerStyle={{ padding: spacing.lg }}>
          <Text style={typography.bodyMuted}>Referencia: {pedido.id}</Text>
          <PaymentPanel orderId={pedido.id} onSucceeded={() => setPaso(3)} />
        </ScrollView>
      )}

      {/* ---------- 4. ENVÍO ---------- */}
      {paso === 3 && (
        <>
          <ScrollView contentContainerStyle={{ padding: spacing.lg }}>
            <SelectorUbicacion value={envio} onChange={setEnvio} />
          </ScrollView>
          <Footer boton="Confirmar envío" onPress={finalizar} />
        </>
      )}
    </View>
  );
}

function Footer({ etiqueta, boton, onPress, atras, deshabilitado }) {
  return (
    <View style={styles.footer}>
      {!!etiqueta && <Text style={[typography.body, { fontWeight: "700", marginBottom: spacing.sm }]}>{etiqueta}</Text>}
      <View style={{ flexDirection: "row" }}>
        {atras && (
          <TouchableOpacity style={[styles.botonSecundario, { marginRight: spacing.sm, marginTop: 0 }]} onPress={atras}>
            <Text style={styles.botonSecundarioTexto}>Atrás</Text>
          </TouchableOpacity>
        )}
        {!!boton && (
          <TouchableOpacity style={[styles.boton, deshabilitado && { opacity: 0.4 }]} onPress={onPress} disabled={deshabilitado}>
            <Text style={styles.botonTexto}>{boton}</Text>
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  centrado: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.background },
  header: { padding: spacing.lg, paddingBottom: spacing.sm },
  stepper: { flexDirection: "row", justifyContent: "space-between", marginTop: spacing.md },
  stepItem: { alignItems: "center", flex: 1 },
  stepPunto: {
    width: 26, height: 26, borderRadius: 13, backgroundColor: colors.border,
    alignItems: "center", justifyContent: "center", marginBottom: spacing.xs,
  },
  stepPuntoActivo: { backgroundColor: colors.primary },
  stepNumero: { fontSize: 12, fontWeight: "700", color: colors.textMuted },
  stepTexto: { fontSize: 12, color: colors.textMuted },
  fila: { flexDirection: "row", alignItems: "center", paddingVertical: spacing.sm, borderBottomWidth: 1, borderBottomColor: colors.border },
  avisoPresupuesto: { backgroundColor: "#FCEAE6", borderRadius: radius.sm, padding: spacing.sm, marginTop: spacing.sm },
  avisoTexto: { color: colors.warning, fontSize: 13, fontWeight: "600", marginTop: spacing.sm },
  footer: { padding: spacing.lg, borderTopWidth: 1, borderTopColor: colors.border, backgroundColor: colors.background },
  boton: { flex: 1, backgroundColor: colors.accent, borderRadius: radius.md, paddingVertical: spacing.md, alignItems: "center" },
  botonTexto: { color: colors.white, fontWeight: "700", fontSize: 15 },
  botonSecundario: {
    borderRadius: radius.md, borderWidth: 1, borderColor: colors.border,
    paddingVertical: spacing.md, paddingHorizontal: spacing.lg, alignItems: "center", marginTop: spacing.md,
  },
  botonSecundarioTexto: { color: colors.primary, fontWeight: "700" },
});
