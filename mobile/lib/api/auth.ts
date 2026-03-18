import { apiClient } from "@/lib/api/client";

export type AuthUser = {
  email: string;
  first_name?: string;
  last_name?: string;
  user_type?: string;
  country?: { code: string; name: string } | null;
  phone_number?: string | null;
  church?: string | null;
  zone?: string | null;
};

export type AuthSession = AuthUser & {
  access: string;
  refresh?: string;
};

export type RegisterPayload = {
  email: string;
  password: string;
  first_name?: string;
  last_name?: string;
  user_type?: string;
};

export const loginRequest = async (email: string, password: string) => {
  const response = await apiClient.post<AuthSession>("token/", { email, password });
  return response.data;
};

export const registerRequest = async (payload: RegisterPayload) => {
  const response = await apiClient.post("users/register/", payload);
  return response.data;
};

export const fetchProfileRequest = async () => {
  const response = await apiClient.get<AuthUser>("users/profile/");
  return response.data;
};

export const logoutRequest = async (refreshToken?: string | null) => {
  if (!refreshToken) return;
  await apiClient.post("users/logout/", { refresh: refreshToken });
};
