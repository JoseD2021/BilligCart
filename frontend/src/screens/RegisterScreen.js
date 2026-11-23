import React, { useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  ActivityIndicator,
} from "react-native";
import { colors, spacing, radius, typography } from "../theme/theme";
import { useAuth } from "../context/AuthContext";

export default function RegisterScreen({ navigation }) {
  const { registrarse, error } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmar, setConfirmar] = useState("");
  const [repartidor, setRepartidor] = useState(false);
  const [errorLocal, setErrorLocal] = useState(null);
  const [info, setInfo] = useState(null);
  const [cargando, setCargando] = useState(false);

  async function handleRegistro() {
    setErrorLocal(null);
    setInfo(null);
    if (!email || !password) {
      setErrorLocal("Completa todos los campos.");
      return;
    }
    if (password !== confirmar) {
      setErrorLocal("Las contraseñas no coinciden.");
      return;
    }
    if (password.length < 6) {
      setErrorLocal("La contraseña debe tener al menos 6 caracteres.");
      return;
    }
    setCargando(true);
    const res = await registrarse({
      email: email.trim(),
      password,
      role: repartidor ? "repartidor" : "user",
    });
    setCargando(false);
    if (res.ok && res.confirmarCorreo) {
      setInfo("Te enviamos un correo para confirmar tu cuenta. Confírmalo y luego inicia sesión.");
    }
  }

  return (
    <KeyboardAvoidingView
      style={styles.screen}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <ScrollView contentContainerStyle={styles.contenido}>
        <Text style={typography.h1}>Crea tu cuenta</Text>
        <Text style={[typography.bodyMuted, { marginBottom: spacing.xl }]}>
          Para empezar a planear tu menú y tu presupuesto semanal.
        </Text>

        <Text style={[typography.label, { marginTop: spacing.md }]}>CORREO</Text>
        <TextInput
          style={styles.input}
          value={email}
          onChangeText={setEmail}
          placeholder="tucorreo@ejemplo.com"
          placeholderTextColor={colors.textMuted}
          autoCapitalize="none"
          keyboardType="email-address"
        />

        <Text style={[typography.label, { marginTop: spacing.md }]}>CONTRASEÑA</Text>
        <TextInput
          style={styles.input}
          value={password}
          onChangeText={setPassword}
          placeholder="Mínimo 6 caracteres"
          placeholderTextColor={colors.textMuted}
          secureTextEntry
        />

        <Text style={[typography.label, { marginTop: spacing.md }]}>CONFIRMAR CONTRASEÑA</Text>
        <TextInput
          style={styles.input}
          value={confirmar}
          onChangeText={setConfirmar}
          placeholder="Repite tu contraseña"
          placeholderTextColor={colors.textMuted}
          secureTextEntry
        />

        <TouchableOpacity
          style={styles.checkFila}
          onPress={() => setRepartidor((v) => !v)}
          activeOpacity={0.8}
        >
          <View style={[styles.checkBox, repartidor && styles.checkBoxActivo]}>
            {repartidor && <Text style={styles.checkTexto}>X</Text>}
          </View>
          <Text style={typography.body}>Registrarme como repartidor</Text>
        </TouchableOpacity>
        <Text style={[typography.bodyMuted, styles.checkAyuda]}>
          {repartidor
            ? "Podrás ver pedidos disponibles y compartir tu ubicación."
            : "Podrás planear menús y comprar ingredientes."}
        </Text>

        {(errorLocal || error) && (
          <Text style={styles.errorTexto}>{errorLocal || error}</Text>
        )}
        {info && <Text style={styles.infoTexto}>{info}</Text>}

        <TouchableOpacity style={styles.boton} onPress={handleRegistro} disabled={cargando}>
          {cargando ? (
            <ActivityIndicator color={colors.white} />
          ) : (
            <Text style={styles.botonTexto}>Crear cuenta</Text>
          )}
        </TouchableOpacity>

        <TouchableOpacity style={styles.linkLogin} onPress={() => navigation.navigate("Login")}>
          <Text style={typography.bodyMuted}>
            ¿Ya tienes cuenta? <Text style={styles.linkTexto}>Inicia sesión</Text>
          </Text>
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  contenido: { flexGrow: 1, justifyContent: "center", padding: spacing.lg },
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    fontSize: 16,
    color: colors.text,
    backgroundColor: colors.surface,
  },
  checkFila: { flexDirection: "row", alignItems: "center", marginTop: spacing.lg },
  checkBox: {
    width: 20,
    height: 20,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 4,
    marginRight: spacing.sm,
    alignItems: "center",
    justifyContent: "center",
  },
  checkBoxActivo: { backgroundColor: colors.primary, borderColor: colors.primary },
  checkTexto: { color: colors.white, fontWeight: "700", fontSize: 13 },
  checkAyuda: { marginTop: spacing.xs },
  errorTexto: { color: colors.warning, marginTop: spacing.sm, fontSize: 13 },
  infoTexto: { color: colors.primary, marginTop: spacing.sm, fontSize: 13, fontWeight: "600" },
  boton: {
    backgroundColor: colors.primary,
    borderRadius: radius.md,
    paddingVertical: spacing.md,
    alignItems: "center",
    marginTop: spacing.lg,
  },
  botonTexto: { color: colors.white, fontWeight: "700", fontSize: 15 },
  linkLogin: { marginTop: spacing.lg, alignItems: "center" },
  linkTexto: { color: colors.primary, fontWeight: "700" },
});
