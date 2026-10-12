
export async function enLotes(items, tarea, concurrencia = 6) {
  let siguiente = 0;
  let fallo = null;

  async function trabajador() {
    while (!fallo && siguiente < items.length) {
      const i = siguiente++;
      try {
        await tarea(items[i], i);
      } catch (e) {
        fallo = fallo ?? e;
      }
    }
  }

  await Promise.all(Array.from({ length: Math.min(concurrencia, items.length) }, trabajador));
  if (fallo) throw fallo;
}
