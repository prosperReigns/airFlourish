import AsyncStorage from "@react-native-async-storage/async-storage";
import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";
import { create } from "zustand";
import { login as authLogin, logout as authLogout } from "../services/auth";
import { setAuthToken } from "../services/api";

const storage = {
  getItem: async (key: string) =>
    Platform.OS === "web"
      ? AsyncStorage.getItem(key)
      : SecureStore.getItemAsync(key),
  setItem: async (key: string, value: string) =>
    Platform.OS === "web"
      ? AsyncStorage.setItem(key, value)
      : SecureStore.setItemAsync(key, value),
  deleteItem: async (key: string) =>
    Platform.OS === "web"
      ? AsyncStorage.removeItem(key)
      : SecureStore.deleteItemAsync(key),
};

interface AuthState {
  user: any;
  token: string | null;
  refreshToken: string | null;
  loading: boolean;

  login: (email: string, password: string) => Promise<string>;
  logout: () => Promise<void>;
  restoreSession: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: null,
  refreshToken: null,
  loading: true,

  login: async (email, password) => {
    const session = await authLogin(email, password);
    const token = session.access;
    const refreshToken = session.refresh ?? null;

    await storage.setItem("token", token);
    if (refreshToken) {
      await storage.setItem("refresh_token", refreshToken);
    }

    setAuthToken(token);
    set({
      token,
      refreshToken,
      user: {
        email: session.email,
        first_name: session.first_name,
        last_name: session.last_name,
        user_type: session.user_type,
        country: session.country ?? null,
        phone_number: session.phone_number ?? null,
        church: session.church ?? null,
        zone: session.zone ?? null,
      },
    });

    return token;
  },

  logout: async () => {
    const refreshToken = get().refreshToken;
    try {
      await authLogout(refreshToken);
    } catch (error) {
      console.log(error);
    }
    await storage.deleteItem("token");
    await storage.deleteItem("refresh_token");
    setAuthToken(null);
    set({ token: null, refreshToken: null, user: null });
  },

  restoreSession: async () => {
    const token = await storage.getItem("token");
    const refreshToken = await storage.getItem("refresh_token");
    if (token) {
      setAuthToken(token);
      set({ token, refreshToken: refreshToken ?? null });
    } else {
      set({ token: null, refreshToken: null });
    }

    set({ loading: false });
  },
}));
