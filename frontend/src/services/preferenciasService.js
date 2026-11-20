import { api } from "./api";

export function getPreferencias() {
  return api.getPreferencias();
}

export function guardarPreferencias(data) {
  return api.guardarPreferencias(data);
}
