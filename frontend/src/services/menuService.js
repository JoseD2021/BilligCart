import { api } from "./api";
import { enLotes } from "./enLotes";

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

/**
 * Lee el menú de la semana actual a través del backend (así no depende de las políticas RLS
 * de Supabase) y lo devuelve listo para las pantallas:
 *   { semanaInicio, dias: [{ dia, comidas: { desayuno, almuerzo, cena } }] }
 * Devuelve null si el usuario aún no tiene menú esta semana.
 *
 *   GET /menu/current                      -> el menú
 *   GET /plato/day/{1..7}?menu_id=         -> los platos de cada día
 *   GET /plato-ingrediente/get-by-plato/id -> cantidades de cada plato
 *   GET /ingrediente/get/{id}              -> nombre, precio y tienda de cada ingrediente
 */
export async function getMenuSemanal() {
  const menu = await api.getMenuActual();
  if (!menu?.id) return null;

  const porDia = await Promise.all([1, 2, 3, 4, 5, 6, 7].map((d) => api.getPlatosPorDia(menu.id, d)));
  const platos = porDia.flat();
  if (platos.length === 0) return null;

  // Ingredientes de cada plato (cantidad y unidad).
  const relacionesPorPlato = new Map();
  await enLotes(platos, async (p) => {
    relacionesPorPlato.set(p.id, (await api.getIngredientesDePlato(p.id)) ?? []);
  });

  // Datos de cada ingrediente (se pide una sola vez por ingrediente). Si uno falla no se cae el menú.
  const ids = new Set();
  for (const rels of relacionesPorPlato.values()) rels.forEach((r) => ids.add(r.ingrediente_id));
  const ingredientes = new Map();
  await enLotes([...ids], async (id) => {
    try {
      ingredientes.set(id, await api.getIngrediente(id));
    } catch (e) {
      console.warn(`getIngrediente(${id}):`, e.message);
    }
  }, 8);

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
      ingredientes: (relacionesPorPlato.get(p.id) ?? []).map((r) => {
        const ing = ingredientes.get(r.ingrediente_id);
        return {
          nombre: ing?.name ?? "Ingrediente",
          cantidad: r.quantity,
          unidad: r.unit,
          precio: ing?.price,
          tienda: ing?.shop,
        };
      }),
    };
  }

  return { semanaInicio: String(menu.week_start ?? "").slice(0, 10), dias };
}
