import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { apiClient, getData } from '@/lib/api';
import { useAuthStore } from '@/stores/auth';
import type { AccountProfile, ApiEnvelope, TokenResponse } from '@/types/api';

export interface Credentials {
  phone_number: string;
  password: string;
}

export function useLogin() {
  const setToken = useAuthStore((state) => state.setToken);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (credentials: Credentials) => {
      const response = await apiClient.post<ApiEnvelope<TokenResponse>>('/auth/login', credentials);
      return response.data.data;
    },
    // Vide le cache : aucune donnee du compte precedent ne doit subsister, sinon
    // l'ancien profil/role reste affiche jusqu'au prochain refetch (bascule lente).
    onSuccess: (data) => {
      setToken(data.access_token);
      queryClient.clear();
    },
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
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await apiClient.post('/auth/logout');
    },
    onSettled: () => {
      clear();
      queryClient.clear();
    },
  });
}
