import api from './axios'
import type { AuthUser, LoginRequest, LoginResponse, RegisterRequest, RegisterResponse } from '@/types'

export const authApi = {
  login: (data: LoginRequest) =>
    api.post<LoginResponse>('/auth/login/', data),

  register: (data: RegisterRequest) =>
    api.post<RegisterResponse>('/auth/register/', data),

  logout: (refresh: string) =>
    api.post('/auth/logout/', { refresh }),

  getProfile: () =>
    api.get<AuthUser>('/auth/profile/'),

  updateProfile: (data: { first_name?: string; last_name?: string }) =>
    api.patch<AuthUser>('/auth/profile/', data),

  changePassword: (data: { old_password: string; new_password: string; new_password_confirm: string }) =>
    api.post('/auth/change-password/', data),
}
