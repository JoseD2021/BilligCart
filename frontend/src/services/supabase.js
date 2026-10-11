
import { Platform } from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { createClient } from "@supabase/supabase-js";

if (Platform.OS !== "web") {
  require("react-native-url-polyfill/auto");
}

const url = process.env.EXPO_PUBLIC_SUPABASE_URL;
const anonKey = process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY;

if (!url || !anonKey) {
  throw new Error(
    "Falta configurar EXPO_PUBLIC_SUPABASE_URL o EXPO_PUBLIC_SUPABASE_ANON_KEY en frontend/.env"
  );
}

if (!url.startsWith("https://") || url.includes("localhost")) {
  throw new Error("EXPO_PUBLIC_SUPABASE_URL no es válida.");
}

if (anonKey.startsWith("sb_secret_")) {
  throw new Error(
    "No uses una clave sb_secret_ en el frontend. Usa sb_publishable_ o la clave anon."
  );
}

export const supabase = createClient(url, anonKey, {
  auth: {
    storage: AsyncStorage,
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: false,
  },
});
