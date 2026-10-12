import { api, ApiError } from "./api";
import { supabase } from "./supabase";
import { getPreferencias } from "./preferenciasService";
import { getMenuSemanal } from "./menuService";
import { enLotes } from "./enLotes";


const DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"];
const MOMENTOS = [
  { clave: "desayuno", tipo: "Desayuno" }, 
  { clave: "almuerzo", tipo: "Almuerzo" },
  { clave: "cena", tipo: "Cena" },
];

export class GeneracionError extends Error {
  constructor(mensaje) {
    super(mensaje);
    this.mensaje = mensaje;
  }
}



function sinAcentos(valor) {
  return String(valor ?? "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim();
}

function capitalizar(texto) {
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}



function construirPrompt(prefs) {
  const restricciones = prefs?.restricciones?.length ? prefs.restricciones.join(", ") : "ninguna";
  const lineas = [`Restricciones alimentarias: ${restricciones}.`];

  if (prefs?.presupuesto_semanal > 0) {
    lineas.push(
      `Presupuesto semanal: $${Number(prefs.presupuesto_semanal).toLocaleString("es-CO")} COP.`
    );
  }

  lineas.push(
    "Genera un desayuno, un almuerzo y una cena distintos para cada día, de lunes a domingo.",
    "Usa ingredientes que se consigan en un supermercado de Colombia, con cantidades para 1 persona.",
    "Nombra los ingredientes en español, en forma genérica y sin marcas (por ejemplo: Arroz, Pechuga de pollo).",
    "Usa unidades simples como g, ml o unidad.",
    "Responde en español."
  );
  return lineas.join(" ");
}

async function pedirMenuALaIA(prompt) {
  try {
    const res = await api.generarConIA(prompt);
    return res?.response;
  } catch (e) {
    if (e instanceof ApiError) {
      if (e.status === 504) {
        throw new GeneracionError("La IA tardó demasiado en responder. Intenta de nuevo en un momento.");
      }
      if (e.status === 502) throw new GeneracionError(e.mensaje); // el backend no está encendido
      throw new GeneracionError(
        "No se pudo contactar a la IA. Verifica que RabbitMQ, el worker y Ollama estén encendidos."
      );
    }
    throw e;
  }
}

function extraerJson(raw) {
  if (raw && typeof raw === "object") return raw;
  const texto = String(raw ?? "");
  const inicio = texto.indexOf("{");
  const fin = texto.lastIndexOf("}");
  if (inicio === -1 || fin <= inicio) {
    throw new GeneracionError("La IA devolvió una respuesta vacía. Intenta de nuevo.");
  }
  try {
    return JSON.parse(texto.slice(inicio, fin + 1));
  } catch (_) {
    throw new GeneracionError("La IA devolvió una respuesta que no se pudo leer. Intenta de nuevo.");
  }
}

// Devuelve el objeto con sus claves sin tildes ni mayúsculas ("Miércoles" -> "miercoles").
function porClave(obj) {
  const salida = {};
  if (obj && typeof obj === "object") {
    for (const [k, v] of Object.entries(obj)) salida[sinAcentos(k)] = v;
  }
  return salida;
}

function interpretarMenu(raw) {
  const json = extraerJson(raw);
  const semana = porClave(json.menuSemanal ?? json.menu ?? json);

  const platos = [];
  let faltan = 0;

  DIAS.forEach((claveDia, i) => {
    const dia = porClave(semana[claveDia]);

    for (const { clave, tipo } of MOMENTOS) {
      const comida = dia[clave];
      const nombre = String(comida?.name ?? comida?.nombre ?? "").trim();
      if (!nombre) {
        faltan += 1;
        continue;
      }

      const vistos = new Set();
      const ingredientes = [];
      const lista = comida.ingredients ?? comida.ingredientes;
      for (const ing of Array.isArray(lista) ? lista : []) {
        const nombreIng = String(ing?.name ?? ing?.nombre ?? "").trim();
        const claveIng = sinAcentos(nombreIng);
        if (!claveIng || vistos.has(claveIng)) continue;
        vistos.add(claveIng);

        const cantidad = Number(ing?.cantidad ?? ing?.quantity);
        ingredientes.push({
          clave: claveIng,
          nombre: capitalizar(nombreIng),
          cantidad: cantidad > 0 ? cantidad : 1,
          unidad: String(ing?.unit ?? ing?.unidad ?? "").trim() || "unidad",
        });
      }

      platos.push({ day: i + 1, tipo, nombre, ingredientes });
    }
  });

  if (faltan > 0) {
    throw new GeneracionError(
      `La IA no devolvió el menú completo (faltaron ${faltan} de 21 comidas). Intenta de nuevo.`
    );
  }
  return platos;
}


async function asegurarMenu() {
  let menu = await api.getMenuActual();
  if (!menu?.id) {
    await api.crearMenu();
    menu = await api.getMenuActual(); // /menu/create no devuelve el id, hay que pedirlo
  }
  if (!menu?.id) throw new GeneracionError("No se pudo crear el menú de esta semana.");
  return menu.id;
}

async function listarPlatos(menuId) {
  const porDia = await Promise.all([1, 2, 3, 4, 5, 6, 7].map((d) => api.getPlatosPorDia(menuId, d)));
  return porDia.flat();
}

async function borrarPlatos(ids) {
  await enLotes(ids, async (id) => {
    await api.eliminarIngredientesDePlato(id);
    await api.eliminarPlato(id);
  });
}


async function revertir(menuId) {
  try {
    const parciales = await listarPlatos(menuId);
    await borrarPlatos(parciales.map((p) => p.id));
  } catch (e) {
    console.warn("No se pudo limpiar la generación fallida:", e.message);
  }
}




async function ingredientesExistentes() {
  const mapa = new Map();
  try {
    const { data, error } = await supabase.from("Ingrediente").select("id, name");
    if (error) throw error;
    for (const fila of data ?? []) {
      const clave = sinAcentos(fila.name);
      if (clave && !mapa.has(clave)) mapa.set(clave, fila.id);
    }
  } catch (e) {
    console.warn("No se pudieron leer los ingredientes existentes:", e.message);
  }
  return mapa;
}


export async function generarMenuSemanal(userId, onProgreso = () => {}) {
  onProgreso("Leyendo tus preferencias...");
  let prefs = null;
  try {
    prefs = await getPreferencias(userId);
  } catch (e) {
    console.warn("getPreferencias:", e.message); // se genera igual, sin restricciones
  }

  onProgreso("La IA está armando tu menú. Puede tardar un par de minutos...");
  const respuesta = await pedirMenuALaIA(construirPrompt(prefs));
  const platos = interpretarMenu(respuesta);

  onProgreso("Preparando tu menú...");
  const menuId = await asegurarMenu();


  const antiguos = await listarPlatos(menuId);
  if (antiguos.length > 0) {
    onProgreso("Reemplazando tu menú anterior...");
    await borrarPlatos(antiguos.map((p) => p.id));
  }

  try {

    let guardados = 0;
    await enLotes(platos, async (p) => {
      await api.crearPlato({
        menu_id: menuId,
        type: p.tipo,
        name: p.nombre,
        day: p.day,
        description: null,
      });
      guardados += 1;
      onProgreso(`Guardando comidas (${guardados}/${platos.length})...`);
    });


    const nuevos = await listarPlatos(menuId);
    const idPorComida = new Map(nuevos.map((p) => [`${p.day}-${sinAcentos(p.type)}`, p.id]));


    onProgreso("Guardando ingredientes...");
    const idPorIngrediente = await ingredientesExistentes();
    const porCrear = new Map();
    for (const p of platos) {
      for (const ing of p.ingredientes) {
        if (!idPorIngrediente.has(ing.clave)) porCrear.set(ing.clave, ing.nombre);
      }
    }
    await enLotes([...porCrear], async ([clave, nombre]) => {
      const fila = await api.crearIngrediente(nombre);
      if (!fila?.id) throw new GeneracionError("No se pudo guardar un ingrediente.");
      idPorIngrediente.set(clave, fila.id);
    });

  
    onProgreso("Uniendo comidas e ingredientes...");
    const relaciones = [];
    for (const p of platos) {
      const platoId = idPorComida.get(`${p.day}-${sinAcentos(p.tipo)}`);
      if (!platoId) throw new GeneracionError("No se pudo guardar el menú completo. Intenta de nuevo.");
      for (const ing of p.ingredientes) {
        relaciones.push({
          quantity: ing.cantidad,
          unit: ing.unidad,
          plato_id: platoId,
          ingrediente_id: idPorIngrediente.get(ing.clave),
        });
      }
    }
    for (let i = 0; i < relaciones.length; i += 50) {
      await api.crearPlatoIngredientes(relaciones.slice(i, i + 50));
    }
  } catch (e) {
    await revertir(menuId);
    throw e;
  }

  return getMenuSemanal(userId);
}
