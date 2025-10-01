import { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { authAPI } from '../api/auth'
import Button from '../components/ui/Button'

export default function Login() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { login, isAuthenticated } = useAuthStore()

  useEffect(() => {
    // If already authenticated, redirect to dashboard
    if (isAuthenticated) {
      navigate('/')
      return
    }

    // Handle OAuth callback
    const code = searchParams.get('code')
    if (code) {
      handleGoogleCallback(code)
    }
  }, [isAuthenticated, searchParams])

  const handleGoogleCallback = async (code: string) => {
    try {
      const { access_token, user } = await authAPI.exchangeGoogleCode(code)
      login(access_token, user)
      navigate('/')
    } catch (error) {
      console.error('Google auth failed:', error)
      alert('Authentication failed. Please try again.')
      navigate('/login')
    }
  }

  const handleGoogleLogin = () => {
    authAPI.loginWithGoogle()
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 via-background to-gray-900">
      <div className="w-full max-w-md p-8 bg-gray-900 rounded-lg shadow-2xl border border-gray-700">
        {/* Logo/Title */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold mb-2">
            <span className="text-primary">BRANE</span>
          </h1>
          <p className="text-gray-400 text-sm">
            Your AI Agents, Your Models, Your Rules
          </p>
        </div>

        {/* Privacy badges */}
        <div className="mb-8 p-4 bg-gray-800 rounded-lg border border-gray-700">
          <h3 className="text-sm font-medium mb-3">Privacy-First Platform</h3>
          <div className="flex gap-2 text-xs">
            <div className="flex-1 p-2 bg-tier-0/10 border border-tier-0 rounded">
              <div className="font-medium text-tier-0">Tier 0</div>
              <div className="text-gray-400">Local Only</div>
            </div>
            <div className="flex-1 p-2 bg-tier-1/10 border border-tier-1 rounded">
              <div className="font-medium text-tier-1">Tier 1</div>
              <div className="text-gray-400">Private Cloud</div>
            </div>
            <div className="flex-1 p-2 bg-tier-2/10 border border-tier-2 rounded">
              <div className="font-medium text-tier-2">Tier 2</div>
              <div className="text-gray-400">Public API</div>
            </div>
          </div>
        </div>

        {/* Google login button */}
        <Button
          variant="primary"
          size="lg"
          className="w-full flex items-center justify-center gap-3"
          onClick={handleGoogleLogin}
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24">
            <path
              fill="currentColor"
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
            />
            <path
              fill="currentColor"
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            />
            <path
              fill="currentColor"
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
            />
            <path
              fill="currentColor"
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
            />
          </svg>
          Sign in with Google
        </Button>

        {/* Info */}
        <p className="mt-6 text-xs text-gray-500 text-center">
          By signing in, you agree to use BRANE responsibly.<br />
          Healthcare/Legal/Finance data requires Tier 0 or Tier 1.
        </p>
      </div>
    </div>
  )
}
