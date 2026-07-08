import { useState } from 'react'
import { useAuth } from '../auth'

const INPUT = 'w-full bg-[#0b0e14] border border-gray-700 rounded px-3 py-2 text-sm text-gray-200'

export default function AuthPage() {
  const { login, signup } = useAuth()
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await (mode === 'login' ? login(email, password) : signup(email, password))
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm rounded-xl border border-gray-800 bg-[#11151c] p-8">
        <h1 className="text-2xl font-semibold text-white">AlphaForge</h1>
        <p className="mb-6 text-xs text-gray-500">Systematic Trading &amp; Research Platform</p>

        <div className="mb-5 grid grid-cols-2 rounded-lg border border-gray-800 p-1 text-sm">
          {['login', 'signup'].map((m) => (
            <button
              key={m}
              onClick={() => { setMode(m); setError(null) }}
              className={`rounded-md py-1.5 capitalize ${
                mode === m ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              {m === 'login' ? 'Log in' : 'Sign up'}
            </button>
          ))}
        </div>

        <form onSubmit={submit} className="space-y-3">
          <label className="block">
            <span className="text-xs text-gray-500">Email</span>
            <input className={INPUT} type="email" required value={email}
                   onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
          </label>
          <label className="block">
            <span className="text-xs text-gray-500">Password (min 6 chars)</span>
            <input className={INPUT} type="password" required minLength={6} value={password}
                   onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
          </label>
          <button
            disabled={busy}
            className="w-full rounded-lg bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50"
          >
            {busy ? 'Please wait…' : mode === 'login' ? 'Log in' : 'Create account'}
          </button>
          {error && <p className="text-xs text-red-400">{error}</p>}
        </form>

        <p className="mt-5 text-center text-[11px] text-gray-600">
          Paper-trading account with ₹10,00,000 simulated cash is created automatically.
        </p>
      </div>
    </div>
  )
}
