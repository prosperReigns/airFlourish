import API from "./api";

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

export type ProfileUpdatePayload = {
  name?: string;
  country?: string;
  phone_number?: string;
  church?: string;
  zone?: string;
};

export const login = async (email: string, password: string) => {
  const response = await API.post<AuthSession>("token/", { email, password });
  return response.data;
};

export const register = async (payload: RegisterPayload) => {
  const response = await API.post("users/register/", payload);
  return response.data;
};

export const fetchProfile = async () => {
  const response = await API.get<AuthUser>("users/profile/");
  return response.data;
};

export const updateProfile = async (payload: ProfileUpdatePayload) => {
  const response = await API.patch<AuthUser>("users/profile/", payload);
  return response.data;
};

export const logout = async (refreshToken?: string | null) => {
  if (!refreshToken) return;
  await API.post("users/logout/", { refresh: refreshToken });
};
