import axios, { type InternalAxiosRequestConfig } from 'axios';

import { useAuthStore } from '@/stores/auth';
import type { ApiEnvelope } from '@/types/api';

// `withCredentials` : envoie le cookie httpOnly du refresh token (meme origine).
export const apiClient = axios.create({ baseURL: '/api/v1', withCredentials: true });

interface RetryConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

apiClient.interceptors.request.use((config) => {
  const { token } = useAuthStore.getState();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let isRefreshing = false;
let waiters: Array<(token: string | null) => void> = [];

function flush(token: string | null) {
  for (const resolve of waiters) {
    resolve(token);
  }
  waiters = [];
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config as RetryConfig | undefined;
    const status = error.response?.status;
    const url = original?.url ?? '';
    const isAuthRoute = url.includes('/auth/login') || url.includes('/auth/refresh');

    if (status !== 401 || !original || original._retry || isAuthRoute) {
      return Promise.reject(error);
    }

    original._retry = true;

    if (isRefreshing) {
      // Une rotation est deja en cours : on attend son issue.
      return new Promise((resolve, reject) => {
        waiters.push((token) => {
          if (!token) {
            reject(error);
            return;
          }
          original.headers.Authorization = `Bearer ${token}`;
          resolve(apiClient(original));
        });
      });
    }

    isRefreshing = true;
    try {
      const response = await apiClient.post<ApiEnvelope<{ access_token: string }>>('/auth/refresh');
      const newToken = response.data.data.access_token;
      useAuthStore.getState().setToken(newToken);
      flush(newToken);
      original.headers.Authorization = `Bearer ${newToken}`;
      return apiClient(original);
    } catch (refreshError) {
      flush(null);
      useAuthStore.getState().clear();
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  },
);

/** Extrait le champ `data` du contrat de reponse uniforme. */
export async function getData<T>(url: string, params?: Record<string, unknown>): Promise<T> {
  const response = await apiClient.get<ApiEnvelope<T>>(url, { params });
  return response.data.data;
}
