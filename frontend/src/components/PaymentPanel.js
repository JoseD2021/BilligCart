import React, { useCallback, useEffect, useRef, useState } from "react";
import { Linking, Text, TouchableOpacity, View } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { api } from "../services/api";
import { colors, spacing, typography } from "../theme/theme";


export default function PaymentPanel({ orderId }) {
  const [payment, setPayment] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const requestKey = useRef(null);
  const alive = useRef(false);

  useFocusEffect(useCallback(() => {
    alive.current = true;
    let active = true;
    const refresh = () => api.getPagoActual(orderId)
      .then((value) => { if (active) setPayment(value); })
      .catch((e) => { if (active) setError(e.message); });
    refresh();
    const timer = setInterval(refresh, 5000);
    return () => { active = false; alive.current = false; clearInterval(timer); };
  }, [orderId]));

  useEffect(() => { requestKey.current = null; setPayment(null); setError(null); }, [orderId]);

  async function requestPayment() {
    if (busy) return;
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
      {!!payment && <Text style={typography.body}>{payment.message}</Text>}
      {!!error && <Text style={{ color: colors.warning }}>{error}</Text>}
      {(!payment || ["failed", "expired"].includes(payment.status)) && (
        <TouchableOpacity disabled={busy} onPress={payment ? retry : requestPayment}>
          <Text style={{ color: colors.primary, paddingVertical: spacing.md }}>
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
