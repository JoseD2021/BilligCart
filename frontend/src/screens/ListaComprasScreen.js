import React, { useCallback, useState } from "react";
import { useFocusEffect } from "@react-navigation/native";
import { View, Text, FlatList, TouchableOpacity, StyleSheet, ActivityIndicator, Alert } from "react-native";
import { colors, spacing, radius, typography } from "../theme/theme";
import { getListaCompras, confirmarCompra } from "../services/comprasService";
import { DIAS_PARA_ACTUALIZAR, idsParaActualizar } from "../services/ingredientesService";

export default function ListaComprasScreen({ navigation }) {
  const [lista, setLista] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [actualizando, setActualizando] = useState(false);
  const [error, setError] = useState(null);
  const [avisoPrecios, setAvisoPrecios] = useState(null);
  const [confirmando, setConfirmando] = useState(false);

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

  if (cargando) {
    return (
      <View style={styles.centrado}>
        <ActivityIndicator color={colors.primary} size="large" />
      </View>
    );
  }

  if (error || !lista?.items?.length) {
    return (
      <View style={styles.centrado}>
        <Text style={typography.body}>{error ?? "Genera un menú para ver tu lista de compras."}</Text>
        <TouchableOpacity onPress={() => cargar()} style={styles.botonConfirmar}>
          <Text style={styles.botonConfirmarTexto}>Actualizar</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const excedePresupuesto = lista.presupuesto > 0 && lista.total > lista.presupuesto;
  const hayPreciosPorActualizar = idsParaActualizar(lista).length > 0;

  async function confirmar() {
    if (confirmando) return;
    setConfirmando(true);
    try {
      const pedido = await confirmarCompra();
      navigation.navigate("Pedido", { pedidoId: pedido.id });
    } catch (e) {
      Alert.alert("No se pudo confirmar", e.message);
    } finally {
      setConfirmando(false);
    }
  }

  return (
    <View style={styles.screen}>
      <View style={styles.header}>
        <Text style={typography.h1}>Lista de compras</Text>
        <View style={styles.resumen}>
          <View>
            <Text style={typography.label}>TOTAL DE REFERENCIA</Text>
            <Text style={[typography.price, excedePresupuesto && { color: colors.warning }]}>
              ${lista.total.toLocaleString("es-CO")}
            </Text>
          </View>
          <View>
            <Text style={typography.label}>PRESUPUESTO</Text>
            <Text style={typography.bodyMuted}>{lista.presupuesto ? `$${lista.presupuesto.toLocaleString("es-CO")}` : "Sin definir"}</Text>
          </View>
        </View>
        <Text style={[typography.bodyMuted, { marginTop: spacing.sm }]}>
          Precios de referencia de los productos encontrados. El costo final depende de la presentación y la cantidad comprada.
        </Text>
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
          <Text style={typography.bodyMuted}>
            Se consultarán los precios con más de {DIAS_PARA_ACTUALIZAR} días sin actualizar.
          </Text>
        )}
        <View style={styles.acciones}>
          <TouchableOpacity onPress={() => cargar({ refrescar: false })} disabled={cargando}
            style={[styles.botonSecundario, cargando && styles.botonDeshabilitado]}>
            <Text style={styles.botonSecundarioTexto}>Actualizar lista</Text>
          </TouchableOpacity>
          {hayPreciosPorActualizar && (
            <TouchableOpacity onPress={() => cargar()} disabled={cargando}
              style={[styles.botonSecundario, cargando && styles.botonDeshabilitado]}>
              <Text style={styles.botonSecundarioTexto}>Actualizar precios</Text>
            </TouchableOpacity>
          )}
        </View>
        {excedePresupuesto && (
          <View style={styles.avisoPresupuesto}>
            <Text style={styles.avisoTexto}>
              Te pasaste del presupuesto por ${(lista.total - lista.presupuesto).toLocaleString("es-CO")}
            </Text>
          </View>
        )}
      </View>

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
            <Text style={typography.price}>{item.precio == null ? "Pendiente" : `$${item.precio.toLocaleString("es-CO")}`}</Text>
          </View>
        )}
      />

      <View style={styles.footer}>
        <TouchableOpacity style={[styles.botonConfirmar, (!lista.puede_confirmar || confirmando) && { opacity: 0.5 }]}
          onPress={confirmar} disabled={!lista.puede_confirmar || confirmando}>
          <Text style={styles.botonConfirmarTexto}>{confirmando ? "Confirmando..." : "Confirmar pedido"}</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  centrado: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.background },
  header: { padding: spacing.lg, paddingBottom: 0 },
  resumen: {
    flexDirection: "row",
    justifyContent: "space-between",
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.md,
    marginTop: spacing.md,
  },
  avisoPresupuesto: {
    backgroundColor: "#FCEAE6",
    borderRadius: radius.sm,
    padding: spacing.sm,
    marginTop: spacing.sm,
  },
  avisoTexto: { color: colors.warning, fontSize: 13, fontWeight: "600" },
  actualizando: { flexDirection: "row", alignItems: "center", gap: spacing.sm, marginTop: spacing.sm },
  acciones: { flexDirection: "row", gap: spacing.sm, marginTop: spacing.sm },
  botonSecundario: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.sm,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
  },
  botonDeshabilitado: { opacity: 0.5 },
  botonSecundarioTexto: { color: colors.primary, fontWeight: "600", fontSize: 13 },
  fila: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  footer: { padding: spacing.lg, borderTopWidth: 1, borderTopColor: colors.border },
  botonConfirmar: {
    backgroundColor: colors.accent,
    borderRadius: radius.md,
    paddingVertical: spacing.md,
    alignItems: "center",
  },
  botonConfirmarTexto: { color: colors.white, fontWeight: "700", fontSize: 15 },
});
