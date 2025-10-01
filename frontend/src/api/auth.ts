import client from './client'
import type { User } from '../types/user'

export interface GoogleAuthResponse {
  access_token: string
  user: User
}

export const authAPI = {
  // Redirect to Google OAuth
  loginWithGoogle: () => {
    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'
    window.location.href = `${API_URL}/auth/google`
  },

  // Exchange code for token (called on callback)
  exchangeGoogleCode: async (code: string): Promise<GoogleAuthResponse> => {
    const response = await client.get(`/auth/google/callback?code=${code}`)
    return response.data
  },

  // Get current user
  getCurrentUser: async (): Promise<User> => {
    const response = await client.get('/auth/me')
    return response.data
  },

  // Logout
  logout: async (): Promise<void> => {
    await client.post('/auth/logout')
  }
}
