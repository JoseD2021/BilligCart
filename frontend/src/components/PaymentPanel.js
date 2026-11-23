import React, { useCallback, useEffect, useRef, useState } from "react";
import { Linking, Text, TouchableOpacity, View } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { api } from "../services/api";
import { colors, spacing, typography } from "../theme/theme";


export default function PaymentPanel({ orderId, onSucceeded }) {
  const [payment, setPayment] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [configuration, setConfiguration] = useState(null);
  const requestKey = useRef(null);
  const alive = useRef(false);
  const inFlight = useRef(false);
  const notifiedPayment = useRef(null);

  useFocusEffect(useCallback(() => {
    alive.current = true;
    let active = true;
    const refresh = () => Promise.all([api.getPagoActual(orderId), api.getConfiguracionPagos()])
      .then(([value, config]) => {
        if (active) { setPayment(value); setConfiguration(config); }
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
  }, [orderId]);

  // Aviso opcional al carrito: cuando Stripe confirma el pago (vía webhook) pasa al siguiente paso.
  useEffect(() => {
    if (payment?.status === "succeeded" && notifiedPayment.current !== payment.id) {
      notifiedPayment.current = payment.id;
      onSucceeded?.();
    }
  }, [payment?.id, payment?.status, onSucceeded]);

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
      {(!payment || ["failed", "expired"].includes(payment.status)) && (
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
