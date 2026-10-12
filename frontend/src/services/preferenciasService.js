import { supabase } from "./supabase";

export async function getPreferencias(userId) {
  const { data, error } = await supabase
    .from("Preferencias")
    .select("restricciones, presupuesto_semanal")
    .eq("user_id", userId)
    .maybeSingle();
  if (error) throw error;
  return data; // null si aún no ha guardado nada
}

export async function guardarPreferencias(userId, { restricciones, presupuesto_semanal }) {
  const { error } = await supabase
    .from("Preferencias")
    .upsert({ user_id: userId, restricciones, presupuesto_semanal }, { onConflict: "user_id" });
  if (error) throw error;
}
