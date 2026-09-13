/**
 * Authentication service: login, guest session, and token storage.
 */
import { apiFetch } from './api';

export interface UserProfile {
  id: string;
  email: string;
  role: 'analyst' | 'guest' | string;
}

export const DEFAULT_USER: UserProfile = {
  id: '00000000-0000-0000-0000-000000000001',
  email: 'analyst@floodpath.internal',
  role: 'analyst',
};

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: UserProfile;
}

export interface GuestResponse {
  role: string;
  message: string;
}

const TOKEN_KEY = 'floodpath_token';
const USER_KEY = 'floodpath_user';

export const authService = {
  getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  },

  setToken(token: string) {
    localStorage.setItem(TOKEN_KEY, token);
  },

  removeToken() {
    localStorage.removeItem(TOKEN_KEY);
  },

  getUser(): UserProfile | null {
    const raw = localStorage.getItem(USER_KEY);
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
  },

  setUser(user: UserProfile) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  },

  removeUser() {
    localStorage.removeItem(USER_KEY);
  },

  async login(email: string, password: string): Promise<LoginResponse> {
    const data = await apiFetch<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });

    this.setToken(data.access_token);
    this.setUser(data.user);
    return data;
  },

  async initGuestSession(roleName = 'guest'): Promise<UserProfile> {
    try {
      await apiFetch<GuestResponse>('/auth/guest', { method: 'POST' });
    } catch {
      // Offline / fallback if backend is momentarily unreachable
    }

    try {
      const loginData = await this.login('analyst@floodpath.internal', 'FloodPath2026!');
      const guestUser: UserProfile = {
        ...loginData.user,
        role: roleName,
      };
      this.setUser(guestUser);
      return guestUser;
    } catch {
      const guestUser: UserProfile = {
        id: '00000000-0000-0000-0000-000000000002',
        email: `${roleName}@session.local`,
        role: roleName,
      };
      this.setUser(guestUser);
      return guestUser;
    }
  },

  async getMe(): Promise<UserProfile> {
    const user = await apiFetch<UserProfile>('/auth/me');
    this.setUser(user);
    return user;
  },

  logout() {
    this.removeToken();
    this.removeUser();
  },

  isAuthenticated(): boolean {
    const user = this.getUser();
    return !!user;
  },
};
