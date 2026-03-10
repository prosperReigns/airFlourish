import * as SecureStore from "expo-secure-store";
import { create } from "zustand";
import API, { setAuthToken } from "../services/api";

interface AuthState {
  user: any;
  token: string | null;
  loading: boolean;

  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  restoreSession: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  loading: true,

  login: async (username, password) => {
    const response = await API.post("token/", {
      username,
      password,
    });

    const token = response.data.access;
    const user = response.data.user;

    await SecureStore.setItemAsync("token", token);

    set({
      token,
      user,
    });

    return token;
  },

  logout: () => {
    setAuthToken(null);
    set({ token: null, user: null });
  },

  restoreSession: async () => {
    const token = await SecureStore.getItemAsync("token");
    if (token) {
      setAuthToken(token);
      set({ token });
    }

    set({ loading: false });
  },
}));
