// Redirect parameters select a screen; only the backend can confirm a payment.
export function paymentOrderFromUrl(value) {
  try {
    const url = new URL(value);
    if (!["success", "cancel"].includes(url.searchParams.get("stripe_return"))) return null;
    const orderId = url.searchParams.get("payment_order_id");
    return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(orderId ?? "")
      ? orderId : null;
  } catch {
    return null;
  }
}
