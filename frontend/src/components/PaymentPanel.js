import React, { useCallback, useEffect, useRef, useState } from "react";
import { Linking, Platform, Text, TouchableOpacity, View } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { api } from "../services/api";
import { colors, spacing, typography } from "../theme/theme";


// autoStart: pide el pago y abre Stripe solo, sin que el usuario toque ningún botón.
// Solo lo hace la primera vez que se entra al pago de un pedido: si ya existe un intento
// (p. ej. volviste de Stripe sin pagar) muestra los botones normales para no redirigir en bucle.
export default function PaymentPanel({ orderId, onSucceeded, autoStart = false }) {
  const [payment, setPayment] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [configuration, setConfiguration] = useState(null);
  const [loaded, setLoaded] = useState(false);
  const [autoRequested, setAutoRequested] = useState(false);
  const autoOpen = useRef(false);
  const requestKey = useRef(null);
  const alive = useRef(false);
  const inFlight = useRef(false);
  const notifiedPayment = useRef(null);

  useFocusEffect(useCallback(() => {
    alive.current = true;
    let active = true;
    const refresh = () => Promise.all([api.getPagoActual(orderId), api.getConfiguracionPagos()])
      .then(([value, config]) => {
        if (active) { setPayment(value); setConfiguration(config); setLoaded(true); }
      })
      .catch((e) => { if (active) setError(e.message); });
    refresh();
    const timer = setInterval(refresh, 5000);
    return () => { active = false; alive.current = false; clearInterval(timer); };
  }, [orderId]));

  useEffect(() => {
    requestKey.current = null;
    setPayment(null);
    setConfiguration(null);
    setError(null);
    setLoaded(false);
    setAutoRequested(false);
    autoOpen.current = false;
  }, [orderId]);

  // Aviso opcional al carrito: cuando Stripe confirma el pago (vía webhook) pasa al siguiente paso.
  useEffect(() => {
    if (payment?.status === "succeeded" && notifiedPayment.current !== payment.id) {
      notifiedPayment.current = payment.id;
      onSucceeded?.();
    }
  }, [payment?.id, payment?.status, onSucceeded]);

  function abrirCheckout(url) {
    // En web se redirige en la misma pestaña (un window.open sin clic lo bloquea el navegador);
    // Stripe devuelve a la app y CarritoScreen recupera el pedido con paymentOrderId.
    if (Platform.OS === "web") {
      window.location.assign(url);
      return;
    }
    Linking.openURL(url).catch(() => setError("No se pudo abrir Stripe."));
  }

  // 1) Sin intento previo y con Stripe configurado: pide el pago automáticamente.
  useEffect(() => {
    if (!autoStart || !loaded || payment || error || autoRequested || !configuration?.ready) return;
    setAutoRequested(true);
    autoOpen.current = true;
    requestPayment();
  }, [autoStart, loaded, payment, error, autoRequested, configuration?.ready]); // eslint-disable-line react-hooks/exhaustive-deps

  // 2) Cuando el backend deja el pago listo (checkout_url), abre Stripe una sola vez.
  useEffect(() => {
    if (!autoOpen.current || !payment?.checkout_url) return;
    autoOpen.current = false;
    abrirCheckout(payment.checkout_url);
  }, [payment?.checkout_url]); // eslint-disable-line react-hooks/exhaustive-deps

  async function requestPayment() {
    if (inFlight.current || !configuration?.ready) return;
    inFlight.current = true;
    setBusy(true);
    setError(null);
    // Same key on uncertain network results. Server also prevents parallel attempts per order.
    requestKey.current ??= `payment-${orderId}-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    try {
      const value = await api.solicitarPago(orderId, requestKey.current);
      if (alive.current) setPayment(value);
    } catch (e) {
      autoOpen.current = false;
      if (alive.current) setError(e.message);
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }

  function retry() {
    requestKey.current = null;
    requestPayment();
  }

  const preparando = autoStart && !payment && !error && (!loaded || autoRequested);

  return (
    <View style={{ marginTop: spacing.lg }}>
      <Text style={typography.h2}>Pago</Text>
      <Text style={typography.bodyMuted}>Stripe TEST: esta operación no mueve dinero real.</Text>
      {!!configuration && (
        <Text style={typography.bodyMuted}>
          Se usará el total guardado del pedido en {configuration.currency?.toUpperCase()}, exclusivamente para una prueba.
          Los precios del carrito siguen siendo de referencia.
        </Text>
      )}
      {configuration?.issues?.map((issue) => <Text key={issue} style={{ color: colors.warning }}>{issue}</Text>)}
      {!!payment && <Text style={typography.body}>{payment.message}</Text>}
      {!!payment?.error && <Text style={{ color: colors.warning }}>{payment.error}</Text>}
      {!!payment && <Text style={typography.bodyMuted}>
        Importe del intento: {(payment.amount_minor / 100).toLocaleString("es-CO", {
          style: "currency", currency: payment.currency.toUpperCase(),
        })}
      </Text>}
      {!!error && <Text style={{ color: colors.warning }}>{error}</Text>}
      {preparando && <Text style={typography.bodyMuted}>Preparando el pago con Stripe...</Text>}
      {!preparando && (!payment || ["failed", "expired"].includes(payment.status)) && (
        <TouchableOpacity disabled={busy || !configuration?.ready} onPress={payment ? retry : requestPayment}>
          <Text style={{ color: colors.primary, paddingVertical: spacing.md, opacity: configuration?.ready ? 1 : 0.5 }}>
            {busy ? "Guardando solicitud..." : payment ? "Reintentar pago" : "Solicitar pago con Stripe"}
          </Text>
        </TouchableOpacity>
      )}
      {!!payment?.checkout_url && (
        <TouchableOpacity onPress={() => Linking.openURL(payment.checkout_url).catch(() => setError("No se pudo abrir Stripe."))}>
          <Text style={{ color: colors.primary, paddingVertical: spacing.md }}>Continuar en Stripe</Text>
        </TouchableOpacity>
      )}
      {payment?.status === "ready" && <Text style={typography.bodyMuted}>Si tu tarjeta es rechazada, puedes volver a intentar en el mismo formulario de Stripe.</Text>}
    </View>
  );
}
