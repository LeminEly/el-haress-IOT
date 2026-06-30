import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { apiClient, getData } from '@/lib/api';
import type {
  AccountSummary,
  Alert,
  AlertRule,
  AlertStatus,
  DashboardSummary,
  Gateway,
  LatestReading,
  PlatformOverview,
  ReadingPoint,
  Sensor,
} from '@/types/api';

// -- Administration plateforme (SUPER_ADMIN) ----------------------------------

export function useAdminOverview() {
  return useQuery({
    queryKey: ['admin', 'overview'],
    queryFn: () => getData<PlatformOverview>('/admin/overview'),
    refetchInterval: 15_000,
  });
}

// -- Capteurs et passerelles --------------------------------------------------

export function useSensors() {
  return useQuery({ queryKey: ['sensors'], queryFn: () => getData<Sensor[]>('/sensors') });
}

export function useUpdateSensor() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      ...body
    }: {
      id: string;
      label?: string;
      kind?: string;
      is_active?: boolean;
      critical_threshold?: number | null;
      color?: string | null;
    }) => apiClient.patch(`/sensors/${id}`, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['sensors'] }),
  });
}

export function useGateways() {
  return useQuery({ queryKey: ['gateways'], queryFn: () => getData<Gateway[]>('/gateways') });
}

export function useCreateGateway() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; base_url: string; poll_interval_seconds: number }) =>
      apiClient.post('/gateways', body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['gateways'] }),
  });
}

// -- Mesures ------------------------------------------------------------------

export function useLatestReadings() {
  return useQuery({
    queryKey: ['readings', 'latest'],
    queryFn: () => getData<LatestReading[]>('/readings/latest'),
    refetchInterval: 5_000,
  });
}

export function useDashboardSummary() {
  return useQuery({
    queryKey: ['dashboard', 'summary'],
    queryFn: () => getData<DashboardSummary>('/dashboard/summary'),
    refetchInterval: 5_000,
  });
}

export function useReadings(
  params: { sensor_id?: string; start?: string; end?: string; limit?: number; offset?: number },
  options?: { refetchInterval?: number },
) {
  return useQuery({
    queryKey: ['readings', params],
    queryFn: () => getData<ReadingPoint[]>('/readings', params),
    ...options,
  });
}

// -- Regles d'alerte ----------------------------------------------------------

export function useAlertRules() {
  return useQuery({
    queryKey: ['alert-rules'],
    queryFn: () => getData<AlertRule[]>('/alert-rules'),
  });
}

export function useCreateAlertRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) => apiClient.post('/alert-rules', body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['alert-rules'] }),
  });
}

export function useDeleteAlertRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiClient.delete(`/alert-rules/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['alert-rules'] }),
  });
}

// -- Alertes ------------------------------------------------------------------

export function useAlerts(status?: AlertStatus) {
  return useQuery({
    queryKey: ['alerts', status ?? 'all'],
    queryFn: () => getData<Alert[]>('/alerts', status ? { status } : undefined),
    refetchInterval: 20_000,
  });
}

export function useAcknowledgeAlert() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiClient.post(`/alerts/${id}/ack`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['alerts'] }),
  });
}

// -- Comptes (SUPER_ADMIN) ----------------------------------------------------

export function useAccounts() {
  return useQuery({
    queryKey: ['accounts'],
    queryFn: () => getData<AccountSummary[]>('/accounts'),
  });
}

export function useCreateAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      phone_number: string;
      password: string;
      company_name: string;
      contact_email?: string;
      language?: 'fr' | 'ar' | 'en';
    }) => apiClient.post('/accounts', body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['accounts'] }),
  });
}

export function useUpdateAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      ...body
    }: {
      id: string;
      company_name?: string;
      contact_email?: string | null;
      language?: 'fr' | 'ar' | 'en';
      status?: 'ACTIVE' | 'SUSPENDED';
    }) => apiClient.patch(`/accounts/${id}`, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['accounts'] }),
  });
}

export function useUpdateAccountStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: 'ACTIVE' | 'SUSPENDED' }) =>
      apiClient.patch(`/accounts/${id}`, { status }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['accounts'] }),
  });
}
