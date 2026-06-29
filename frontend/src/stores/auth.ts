import { create } from 'zustand';

import type { AccountProfile } from '@/types/api';

const TOKEN_KEY = 'el-haress-token';

interface AuthState {
  token: string | null;
  account: AccountProfile | null;
  setToken: (token: string) => void;
  setAccount: (account: AccountProfile | null) => void;
  clear: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem(TOKEN_KEY),
  account: null,
  setToken: (token) => {
    localStorage.setItem(TOKEN_KEY, token);
    set({ token });
  },
  setAccount: (account) => set({ account }),
  clear: () => {
    localStorage.removeItem(TOKEN_KEY);
    set({ token: null, account: null });
  },
}));
