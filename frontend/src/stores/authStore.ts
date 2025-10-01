import { create } from 'zustand'
import type { User } from '../types/user'

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean

  login: (token: string, user: User) => void
  logout: () => void
  initialize: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  isAuthenticated: false,

  login: (token: string, user: User) => {
    localStorage.setItem('brane_token', token)
    localStorage.setItem('brane_user', JSON.stringify(user))
    set({ token, user, isAuthenticated: true })
  },

  logout: () => {
    localStorage.removeItem('brane_token')
    localStorage.removeItem('brane_user')
    set({ token: null, user: null, isAuthenticated: false })
  },

  initialize: () => {
    const token = localStorage.getItem('brane_token')
    const userStr = localStorage.getItem('brane_user')

    if (token && userStr) {
      try {
        const user = JSON.parse(userStr)
        set({ token, user, isAuthenticated: true })
      } catch {
        // Invalid stored data, clear it
        localStorage.removeItem('brane_token')
        localStorage.removeItem('brane_user')
      }
    }
  }
}))
