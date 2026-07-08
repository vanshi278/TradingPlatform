import { createContext, useContext, useEffect, useState } from 'react'

const AuthCtx = createContext(null)
export const useAuth = () => useContext(AuthCtx)

export function getToken() {
  return localStorage.getItem('af_token')
}

/** fetch() with the Bearer token attached; auto-logout on 401. */
export async function authFetch(path, opts = {}) {
  const token = getToken()
  const r = await fetch(path, {
    ...opts,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(opts.headers || {}),
    },
  })
  if (r.status === 401) {
    localStorage.removeItem('af_token')
    localStorage.removeItem('af_email')
    window.dispatchEvent(new Event('af-logout'))
  }
  return r
}

export function AuthProvider({ children }) {
  const [email, setEmail] = useState(localStorage.getItem('af_email'))
  const authed = Boolean(email && getToken())

  useEffect(() => {
    const onLogout = () => setEmail(null)
    window.addEventListener('af-logout', onLogout)
    return () => window.removeEventListener('af-logout', onLogout)
  }, [])

  const submit = async (mode, em, password) => {
    const r = await fetch(`/api/auth/${mode}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: em, password }),
    })
    const data = await r.json()
    if (!r.ok) throw new Error(data.detail || `${mode} failed`)
    localStorage.setItem('af_token', data.token)
    localStorage.setItem('af_email', data.user.email)
    setEmail(data.user.email)
  }

  const logout = () => {
    localStorage.removeItem('af_token')
    localStorage.removeItem('af_email')
    setEmail(null)
  }

  return (
    <AuthCtx.Provider
      value={{
        authed,
        email,
        login: (e, p) => submit('login', e, p),
        signup: (e, p) => submit('signup', e, p),
        logout,
      }}
    >
      {children}
    </AuthCtx.Provider>
  )
}
