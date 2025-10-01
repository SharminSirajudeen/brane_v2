import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

const client = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor: Add auth token
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('brane_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor: Handle 401 (logout)
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('brane_token')
      localStorage.removeItem('brane_user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default client
