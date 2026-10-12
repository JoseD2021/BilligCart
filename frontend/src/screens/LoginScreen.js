import React, { useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
} from "react-native";
import { colors, spacing, radius, typography } from "../theme/theme";
import { useAuth } from "../context/AuthContext";

export default function LoginScreen({ navigation }) {
  const { iniciarSesion, error } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [cargando, setCargando] = useState(false);

  async function handleLogin() {
    if (!email || !password) return;
    setCargando(true);
    await iniciarSesion(email.trim(), password);
    setCargando(false);
  }

  return (
    <KeyboardAvoidingView
      style={styles.screen}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <View style={styles.contenido}>
        <Text style={styles.logo}>🥗</Text>
        <Text style={typography.h1}>Bienvenido de vuelta</Text>
        <Text style={[typography.bodyMuted, { marginBottom: spacing.xl }]}>
          Inicia sesión para ver tu menú y tu presupuesto.
        </Text>

        <Text style={typography.label}>CORREO</Text>
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
          placeholder="••••••••"
          placeholderTextColor={colors.textMuted}
          secureTextEntry
        />

        {error && <Text style={styles.errorTexto}>{error}</Text>}

        <TouchableOpacity style={styles.boton} onPress={handleLogin} disabled={cargando}>
          {cargando ? (
            <ActivityIndicator color={colors.white} />
          ) : (
            <Text style={styles.botonTexto}>Iniciar sesión</Text>
          )}
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.linkRegistro}
          onPress={() => navigation.navigate("Registro")}
        >
          <Text style={typography.bodyMuted}>
            ¿No tienes cuenta? <Text style={styles.linkTexto}>Regístrate</Text>
          </Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  contenido: { flex: 1, justifyContent: "center", paddingHorizontal: spacing.lg },
  logo: { fontSize: 48, marginBottom: spacing.md },
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
  errorTexto: { color: colors.warning, marginTop: spacing.sm, fontSize: 13 },
  boton: {
    backgroundColor: colors.primary,
    borderRadius: radius.md,
    paddingVertical: spacing.md,
    alignItems: "center",
    marginTop: spacing.lg,
  },
  botonTexto: { color: colors.white, fontWeight: "700", fontSize: 15 },
  linkRegistro: { marginTop: spacing.lg, alignItems: "center" },
  linkTexto: { color: colors.primary, fontWeight: "700" },
});
