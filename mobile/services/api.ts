import { useAuthStore } from "@/store/authStore";
import axios from "axios";

const API = axios.create({
  baseURL: "http://192.168.0.200:8000/api/",
});

// Attach token automatically
API.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token;

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => Promise.reject(error),
);

export default API;
