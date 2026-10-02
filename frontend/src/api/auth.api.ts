import type { LoginResponse } from '../types/pmv1'
import { apiFetch } from './client'

export interface LoginCredentials {
  email: string
  password: string
}

export async function loginApi(credentials: LoginCredentials): Promise<LoginResponse> {
  return apiFetch<LoginResponse>('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify({
      email: credentials.email.trim().toLowerCase(),
      password: credentials.password,
    }),
  })
}
