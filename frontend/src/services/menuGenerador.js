import { api, ApiError } from "./api";
import { getPreferencias } from "./preferenciasService";
import { getMenuSemanal } from "./menuService";


const COMIDAS_POR_SEMANA = 21;
const ESPERA_MAXIMA_MS = 300000; // 5 minutos
const INTERVALO_ESPERA_MS = 10000; // 10 segundos

export class GeneracionError extends Error {
  constructor(mensaje) {
    super(mensaje);
    this.mensaje = mensaje;
  }
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

// resumir el menu para poder comparar si cambió
function firmaMenu(menu) {
  if (!menu?.dias?.length) return "";
  return menu.dias
    .map((dia) =>
      Object.entries(dia.comidas ?? {})
        .map(([tipo, comida]) => `${tipo}:${comida?.nombre ?? ""}`)
        .sort()
        .join("|")
    )
    .join("~");
}

function contarComidas(menu) {
  return (menu?.dias ?? []).reduce(
    (total, dia) => total + Object.keys(dia.comidas ?? {}).length,
    0
  );
}

async function leerMenuSeguro(userId) {
  try {
    return await getMenuSemanal(userId);
  } catch (e) {
    console.warn("getMenuSemanal:", e.message);
    return null;
  }
}

// espera hasta que el menú generado por la IA se haya guardado en el backend, o hasta que se agote el tiempo
async function esperarMenuPersistido(userId, firmaAnterior, onProgreso) {
  const limite = Date.now() + ESPERA_MAXIMA_MS;

  while (Date.now() < limite) {
    const menu = await leerMenuSeguro(userId);
    if (menu && contarComidas(menu) >= COMIDAS_POR_SEMANA && firmaMenu(menu) !== firmaAnterior) {
      return menu;
    }

    onProgreso("Guardando tu menú en el servidor...");
    await new Promise((resolve) => setTimeout(resolve, INTERVALO_ESPERA_MS));
  }

  throw new GeneracionError(
    "Tu menú se está guardando y está tardando más de lo esperado. Intenta recargar en un momento."
  );
}


export async function generarMenuSemanal(userId, onProgreso = () => {}) {
  onProgreso("Leyendo tus preferencias...");
  let prefs = null;
  try {
    prefs = await getPreferencias(userId);
  } catch (e) {
    console.warn("getPreferencias:", e.message); // se genera igual, sin restricciones
  }

  const firmaAnterior = firmaMenu(await leerMenuSeguro(userId));

  onProgreso("La IA está armando tu menú. Puede tardar un par de minutos...");
  // ejecutar la generacion del menu en el backend
  await pedirMenuALaIA(construirPrompt(prefs));

  onProgreso("Guardando tu menú en el servidor...");
  return esperarMenuPersistido(userId, firmaAnterior, onProgreso);
}
