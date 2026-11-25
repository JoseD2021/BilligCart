import React, { useEffect, useRef, useState } from "react";
import { View, Text, TextInput, StyleSheet } from "react-native";
import { colors, spacing, radius, typography } from "../theme/theme";
import { buscarCoordenadas } from "../services/ubicacionService";
import UbicacionMapa from "./UbicacionMapa";

export default function SelectorUbicacion({ value, onChange }) {
  const [buscando, setBuscando] = useState(false);
  const [sinResultado, setSinResultado] = useState(false);
  const valueRef = useRef(value);
  const onChangeRef = useRef(onChange);
  valueRef.current = value;
  onChangeRef.current = onChange;

  const direccion = value?.direccion ?? "";

  useEffect(() => {
    const texto = direccion.trim();
    if (texto.length < 5) {
      setBuscando(false);
      setSinResultado(false);
      return undefined;
    }
    let active = true;
    const controller = typeof AbortController !== "undefined" ? new AbortController() : null;
    setBuscando(true);
    setSinResultado(false);
    const timer = setTimeout(() => {
      buscarCoordenadas(texto, controller?.signal)
        .then((coords) => {
          if (!active) return;
          setBuscando(false);
          setSinResultado(!coords);
          onChangeRef.current({
            ...valueRef.current,
            lat: coords?.lat ?? null,
            lng: coords?.lng ?? null,
          });
        })
        .catch((error) => {
          if (!active || controller?.signal.aborted) return;
          setBuscando(false);
          setSinResultado(true);
          console.warn("[dirección] no se pudo ubicar en el mapa", error);
        });
    }, 700);
    return () => { active = false; clearTimeout(timer); controller?.abort(); };
  }, [direccion]);

  function cambiarCampo(campo, texto) {
    onChangeRef.current({
      ...valueRef.current,
      [campo]: texto,
      ...(campo === "direccion" ? { lat: null, lng: null } : {}),
    });
  }

  return (
    <View>
      <UbicacionMapa
        lat={value?.lat}
        lng={value?.lng}
        direccion={direccion}
        buscando={buscando}
        sinResultado={sinResultado}
      />
      <Text style={typography.label}>DIRECCIÓN DE ENTREGA</Text>
      <TextInput
        style={styles.input}
        placeholder="Calle 100 # 15-20, apto 301"
        placeholderTextColor={colors.textMuted}
        value={direccion}
        onChangeText={(texto) => cambiarCampo("direccion", texto)}
      />
      <Text style={[typography.label, { marginTop: spacing.md }]}>REFERENCIA (OPCIONAL)</Text>
      <TextInput
        style={styles.input}
        placeholder="Portería, torre, punto de referencia..."
        placeholderTextColor={colors.textMuted}
        value={value?.referencia ?? ""}
        onChangeText={(texto) => cambiarCampo("referencia", texto)}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  input: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.sm,
    padding: spacing.md,
    marginTop: spacing.xs,
    fontSize: 15,
    color: colors.text,
  },
});
