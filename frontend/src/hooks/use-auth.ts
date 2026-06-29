import { useMutation, useQuery } from '@tanstack/react-query';

import { apiClient, getData } from '@/lib/api';
import { useAuthStore } from '@/stores/auth';
import type { AccountProfile, ApiEnvelope, TokenResponse } from '@/types/api';

export interface Credentials {
  phone_number: string;
  password: string;
}

export function useLogin() {
  const setToken = useAuthStore((state) => state.setToken);
  return useMutation({
    mutationFn: async (credentials: Credentials) => {
      const response = await apiClient.post<ApiEnvelope<TokenResponse>>('/auth/login', credentials);
      return response.data.data;
    },
    onSuccess: (data) => setToken(data.access_token),
  });
}

export function useMe() {
  const token = useAuthStore((state) => state.token);
  return useQuery({
    queryKey: ['me'],
    queryFn: () => getData<AccountProfile>('/auth/me'),
    enabled: Boolean(token),
    staleTime: 60_000,
  });
}

export function useLogout() {
  const clear = useAuthStore((state) => state.clear);
  return useMutation({
    mutationFn: async () => {
      await apiClient.post('/auth/logout');
    },
    onSettled: () => clear(),
  });
}
