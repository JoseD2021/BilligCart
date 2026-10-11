import { supabase } from "./supabase";

const DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];


function normalizarTipo(valor) {
  const s = String(valor ?? "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
  if (s.startsWith("desay") || s.startsWith("break")) return "desayuno";
  if (s.startsWith("almu") || s.startsWith("lunch")) return "almuerzo";
  if (s.startsWith("cen") || s.startsWith("dinner")) return "cena";
  return null;
}


export async function getMenuSemanal(userId) {
  const { data, error } = await supabase
    .from("Menu")
    .select(
      `id, week_start,
       Plato ( id, type, name, description, day,
         PlatoIngrediente ( quantity, unit,
           Ingrediente ( name, price, shop ) ) )`
    )
    .eq("user_id", userId)
    .order("week_start", { ascending: false })
    .limit(1)
    .maybeSingle();

  if (error) throw error;
  if (!data) return null;

  const platos = data.Plato ?? [];
  if (platos.length === 0) return null;

  // Plato.day: acepta 1-7 o 0-6, siempre con Lunes primero.
  const base = platos.some((p) => p.day === 0) ? 0 : 1;

  const dias = DIAS.map((dia) => ({ dia, comidas: {} }));
  for (const p of platos) {
    const tipo = normalizarTipo(p.type);
    const destino = dias[p.day - base];
    if (!tipo || !destino) continue;
    destino.comidas[tipo] = {
      nombre: p.name,
      descripcion: p.description,
      ingredientes: (p.PlatoIngrediente ?? []).map((pi) => ({
        nombre: pi.Ingrediente?.name,
        cantidad: pi.quantity,
        unidad: pi.unit,
        precio: pi.Ingrediente?.price,
        tienda: pi.Ingrediente?.shop,
      })),
    };
  }

  return { semanaInicio: data.week_start, dias };
}

/**
 * Solo desarrollo: crea un menú de ejemplo para el usuario logueado llamando a la función
 * SQL crear_menu_demo() (definida en supabase_menu.sql). Es idempotente.
 */
export async function crearMenuDemo(userId) {
  const { error } = await supabase.rpc("crear_menu_demo");
  if (error) throw error;
  return getMenuSemanal(userId);
}
