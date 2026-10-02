const TOKEN_KEY = 'siprim:access-token'

export function loadAccessToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function saveAccessToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearAccessToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}
