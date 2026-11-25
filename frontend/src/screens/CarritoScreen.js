import React, { useCallback, useEffect, useState } from "react";
import {
  View, Text, FlatList, ScrollView, TouchableOpacity, StyleSheet, ActivityIndicator,
} from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import Alerta from "../components/Alerta";
import Card from "../components/Card";
import PaymentPanel from "../components/PaymentPanel";
import SelectorUbicacion from "../components/SelectorUbicacion";
import { colors, spacing, radius, typography } from "../theme/theme";
import { getListaCompras, confirmarCompra } from "../services/comprasService";
import { idsParaActualizar } from "../services/ingredientesService";
import { api } from "../services/api";

const PASOS = ["Productos", "Total", "Dirección", "Pago"];
const pesos = (n) => `$${Number(n).toLocaleString("es-CO")}`;

// Misma regla que el backend: un único precio de referencia por ingrediente,
// aunque aparezca en varias filas (unidades distintas).
function totalDe(items) {
  const precios = new Map(items.map((item) => [item.ingrediente_id, item.precio]));
  return Math.round([...precios.values()].reduce((suma, precio) => suma + (precio ?? 0), 0) * 100) / 100;
}

export default function CarritoScreen({ navigation, route }) {
  const returnOrderId = route?.params?.paymentOrderId;
  const [paso, setPaso] = useState(returnOrderId ? 3 : 0);
  const [lista, setLista] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);
  const [pedido, setPedido] = useState(null); // se crea al confirmar (paso Total -> Pago)
  const [confirmando, setConfirmando] = useState(false);
  const [actualizando, setActualizando] = useState(false);
  const [avisoPrecios, setAvisoPrecios] = useState(null);
  const [alerta, setAlerta] = useState(null);
  const [deseleccionados, setDeseleccionados] = useState(() => new Set()); // ids que el usuario desmarcó
  const [envio, setEnvio] = useState({ direccion: "", referencia: "", lat: null, lng: null });

  // Productos y precios: salen de /compras. El servicio consulta precios viejos
  // antes de mostrar la lista final, igual que en Lista de compras.
  const cargar = useCallback(({ refrescar = true } = {}) => {
    let active = true;
    setCargando(true);
    setError(null);
    setAvisoPrecios(null);
    getListaCompras({
      refrescar,
      onLista: (datos) => {
        if (!active) return;
        setLista(datos);
        setCargando(false);
      },
      onActualizando: () => { if (active) setActualizando(true); },
    })
      .then(({ lista: datos, actualizacion }) => {
        if (!active) return;
        setLista(datos);
        if (actualizacion?.actualizados > 0) {
          setAvisoPrecios(`Precios actualizados para ${actualizacion.actualizados} ingredientes.`);
        } else if (actualizacion?.errores.length) {
          setAvisoPrecios(`No se pudieron actualizar ${actualizacion.errores.length} precios. Puedes reintentar.`);
        }
      })
      .catch((e) => { if (active) setError(e.message); })
      .finally(() => {
        if (!active) return;
        setActualizando(false);
        setCargando(false);
      });
    return () => { active = false; };
  }, []);
  useFocusEffect(cargar);

  // Stripe reloads the web app. Recover the owned order instead of creating it again.
  useEffect(() => {
    if (!returnOrderId) return;
    let active = true;
    setPaso(3);
    setPedido(null);
    api.getEstadoPedido(returnOrderId)
      .then((value) => { if (active) setPedido(value); })
      .catch((e) => { if (active) { setError(e.message); setPaso(0); } });
    return () => { active = false; };
  }, [returnOrderId]);

  function alternar(item) {
    setDeseleccionados((previo) => {
      const siguiente = new Set(previo);
      if (siguiente.has(item.id)) siguiente.delete(item.id);
      else siguiente.add(item.id);
      return siguiente;
    });
  }

  function alternarTodos() {
    const todosMarcados = seleccionados.length === conPrecio.length;
    setDeseleccionados(todosMarcados ? new Set(conPrecio.map((item) => item.id)) : new Set());
  }

  // Paso Dirección -> Pago: crea el pedido con los productos marcados, le guarda la dirección
  // y recién ahí pasa al pago. Si se repite con la misma selección, el backend devuelve el mismo pedido.
  async function confirmarDireccion() {
    if (confirmando) return;
    if (!envio.direccion.trim()) {
      setAlerta({ titulo: "Falta la dirección", mensaje: "Escribe la dirección de entrega para continuar." });
      return;
    }
    setConfirmando(true);
    try {
      const creado = await confirmarCompra({ itemsIds: seleccionados.map((item) => item.id) });
      // lat/lng los completa el mapa al ubicar la dirección; si no, viajan en null.
      await api.guardarEnvio(creado.id, {
        direccion: envio.direccion.trim(),
        referencia: envio.referencia?.trim() || null,
        lat: envio.lat ?? null,
        lng: envio.lng ?? null,
      });
      setPedido(creado);
      setPaso(3);
    } catch (e) {
      setAlerta({ titulo: "No se pudo continuar", mensaje: e.message });
    } finally {
      setConfirmando(false);
    }
  }

  // Pago exitoso: limpia el carrito y abre el seguimiento del pedido (envío).
  function irAlPedido() {
    const pedidoId = pedido.id;
    setPaso(0);
    setPedido(null);
    setEnvio({ direccion: "", referencia: "", lat: null, lng: null });
    setAlerta(null);
    setDeseleccionados(new Set());
    navigation.setParams({ paymentOrderId: undefined });
    navigation.navigate("Pedido", { screen: "Pedidos", params: { pedidoId } });
  }

  // Selección de productos: solo se pueden marcar los que tienen precio.
  const itemsLista = lista?.items ?? [];
  const conPrecio = itemsLista.filter((item) => item.precio != null);
  const itemsSinPrecio = itemsLista.filter((item) => item.precio == null);
  const seleccionados = conPrecio.filter((item) => !deseleccionados.has(item.id));
  const noIncluidos = itemsLista.filter((item) => !seleccionados.includes(item));
  const totalSeleccion = totalDe(seleccionados);

  if ((cargando && !lista && paso < 3) || (paso === 3 && !pedido)) {
    return <View style={styles.centrado}><ActivityIndicator color={colors.primary} size="large" /></View>;
  }

  if ((error || !lista?.items?.length) && paso < 3) {
    return (
      <View style={styles.centrado}>
        <Text style={[typography.body, { textAlign: "center", paddingHorizontal: spacing.lg }]}>
          {error ?? "Genera un menú para ver tu lista de compras."}
        </Text>
        <TouchableOpacity onPress={() => cargar()} style={styles.botonSecundario}>
          <Text style={styles.botonSecundarioTexto}>Actualizar</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const excedePresupuesto = (lista?.presupuesto ?? 0) > 0 && totalSeleccion > lista.presupuesto;
  const hayPreciosPorActualizar = lista ? idsParaActualizar(lista).length > 0 : false;
  const puedeConfirmar = !!lista?.menu_completo && seleccionados.length > 0;

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
          <View style={styles.accionesProductos}>
            <TouchableOpacity onPress={alternarTodos} disabled={conPrecio.length === 0}>
              <Text style={styles.link}>
                {seleccionados.length === conPrecio.length ? "Quitar todos" : "Seleccionar todos"}
              </Text>
            </TouchableOpacity>
            {lista.precios_pendientes > 0 && (
              <Text style={styles.avisoTexto}>Faltan precios para {lista.precios_pendientes} ingredientes.</Text>
            )}
            {actualizando && (
              <View style={styles.actualizando}>
                <ActivityIndicator color={colors.primary} size="small" />
                <Text style={typography.bodyMuted}>Consultando precios...</Text>
              </View>
            )}
            {avisoPrecios && <Text style={typography.bodyMuted}>{avisoPrecios}</Text>}
            {hayPreciosPorActualizar && (
              <TouchableOpacity onPress={() => cargar({ refrescar: true })}
                disabled={actualizando}
                style={[styles.botonSecundario, actualizando && styles.botonDeshabilitado]}>
                <Text style={styles.botonSecundarioTexto}>Actualizar precios</Text>
              </TouchableOpacity>
            )}
          </View>
          <FlatList
            data={lista.items}
            keyExtractor={(item) => item.id}
            contentContainerStyle={{ padding: spacing.lg }}
            renderItem={({ item }) => {
              const sinPrecio = item.precio == null;
              const marcado = !sinPrecio && !deseleccionados.has(item.id);
              return (
                <TouchableOpacity
                  style={[styles.fila, !marcado && styles.filaApagada]}
                  onPress={() => alternar(item)}
                  disabled={sinPrecio}
                  activeOpacity={0.7}
                >
                  <View style={[styles.checkCaja, styles.checkProducto, marcado && styles.checkActivo]}>
                    {marcado && <Text style={styles.checkMarca}>✓</Text>}
                  </View>
                  <View style={{ flex: 1 }}>
                    <Text style={typography.body}>{item.nombre}</Text>
                    <Text style={typography.bodyMuted}>{item.cantidad} {item.unidad} · {item.supermercado ?? "Sin cotizar"}</Text>
                  </View>
                  <Text style={typography.price}>{sinPrecio ? "Sin precio" : pesos(item.precio)}</Text>
                </TouchableOpacity>
              );
            }}
          />
          <Footer
            etiqueta={`${seleccionados.length} de ${conPrecio.length} productos · ${pesos(totalSeleccion)}`}
            boton="Ver total"
            deshabilitado={seleccionados.length === 0}
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
                {pesos(totalSeleccion)}
              </Text>
              <Text style={[typography.bodyMuted, { marginTop: spacing.xs }]}>
                Presupuesto: {lista.presupuesto ? pesos(lista.presupuesto) : "Sin definir"}
              </Text>
              {excedePresupuesto && (
                <View style={styles.avisoPresupuesto}>
                  <Text style={styles.avisoTexto}>Te pasaste del presupuesto por {pesos(totalSeleccion - lista.presupuesto)}</Text>
                </View>
              )}
            </Card>
            <Text style={typography.bodyMuted}>
              Precios de referencia de los productos encontrados. El costo final depende de la presentación y la cantidad comprada.
            </Text>
            {noIncluidos.length > 0 && (
              <View style={styles.avisoIngredientes}>
                <Text style={styles.avisoTexto}>No se incluirán estos productos:</Text>
                {noIncluidos.map((item) => (
                  <Text key={item.id} style={typography.bodyMuted}>
                    • {item.nombre} — {item.cantidad} {item.unidad}{item.precio == null ? " (sin precio)" : ""}
                  </Text>
                ))}
              </View>
            )}
            {!lista.menu_completo && (
              <Text style={styles.avisoTexto}>Completa el menú semanal para poder confirmar.</Text>
            )}
          </ScrollView>
          <Footer
            etiqueta={`${seleccionados.length} productos · ${pesos(totalSeleccion)}`}
            boton="Continuar"
            deshabilitado={!puedeConfirmar}
            onPress={() => setPaso(2)}
            atras={() => setPaso(0)}
          />
        </>
      )}

      {/* ---------- 3. DIRECCIÓN (se guarda en el pedido; el mapa/GPS se conecta en SelectorUbicacion) ---------- */}
      {paso === 2 && (
        <>
          <ScrollView contentContainerStyle={{ padding: spacing.lg }}>
            <Alerta {...alerta} onCerrar={() => setAlerta(null)} />
            <SelectorUbicacion value={envio} onChange={setEnvio} />
          </ScrollView>
          <Footer
            boton={confirmando ? "Guardando..." : "Confirmar dirección y pagar"}
            deshabilitado={confirmando}
            onPress={confirmarDireccion}
            atras={() => setPaso(1)}
          />
        </>
      )}

      {/* ---------- 4. PAGO (Stripe Checkout, el PaymentPanel del proyecto) ---------- */}
      {paso === 3 && pedido && (
        <ScrollView contentContainerStyle={{ padding: spacing.lg }}>
          <Text style={typography.bodyMuted}>Referencia: {pedido.id}</Text>
          <PaymentPanel orderId={pedido.id} autoStart onSucceeded={irAlPedido} />
        </ScrollView>
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
  avisoIngredientes: {
    backgroundColor: "#FCEAE6", borderRadius: radius.sm, padding: spacing.md, marginTop: spacing.sm,
  },
  opcionFila: { flexDirection: "row", alignItems: "center", gap: spacing.sm, marginTop: spacing.sm },
  checkCaja: {
    width: 20, height: 20, borderRadius: radius.sm, borderWidth: 1, borderColor: colors.primary,
    alignItems: "center", justifyContent: "center",
  },
  checkActivo: { backgroundColor: colors.primary },
  checkProducto: { marginRight: spacing.md },
  filaApagada: { opacity: 0.55 },
  link: { color: colors.primary, fontWeight: "600", fontSize: 14, marginTop: spacing.sm },
  checkMarca: { color: colors.white, fontWeight: "700", fontSize: 13 },
  avisoTexto: { color: colors.warning, fontSize: 13, fontWeight: "600", marginTop: spacing.sm },
  accionesProductos: { paddingHorizontal: spacing.lg },
  actualizando: { flexDirection: "row", alignItems: "center", gap: spacing.sm, marginTop: spacing.sm },
  botonDeshabilitado: { opacity: 0.5 },
  footer: { padding: spacing.lg, borderTopWidth: 1, borderTopColor: colors.border, backgroundColor: colors.background },
  boton: { flex: 1, backgroundColor: colors.accent, borderRadius: radius.md, paddingVertical: spacing.md, alignItems: "center" },
  botonTexto: { color: colors.white, fontWeight: "700", fontSize: 15 },
  botonSecundario: {
    borderRadius: radius.md, borderWidth: 1, borderColor: colors.border,
    paddingVertical: spacing.md, paddingHorizontal: spacing.lg, alignItems: "center", marginTop: spacing.md,
  },
  botonSecundarioTexto: { color: colors.primary, fontWeight: "700" },
});
