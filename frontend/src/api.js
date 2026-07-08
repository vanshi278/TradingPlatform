import { authFetch } from './auth'

export async function runBacktest(params) {
  const r = await fetch('/api/backtest/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
  if (!r.ok) throw new Error(`backtest failed: ${r.status}`)
  return r.json()
}

export function marketSocket(symbol = 'RELIANCE') {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  return new WebSocket(`${proto}://${location.host}/ws/market?symbol=${symbol}`)
}

async function json(r) {
  const data = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(data.detail || `request failed: ${r.status}`)
  return data
}

// ---- trading ----
export const getSymbols = () => fetch('/api/market/symbols').then((r) => r.json())
export const getPortfolio = () => authFetch('/api/trading/portfolio').then(json)
export const getOrders = () => authFetch('/api/trading/orders').then(json)
export const placeOrder = (body) =>
  authFetch('/api/trading/orders', { method: 'POST', body: JSON.stringify(body) }).then(json)
export const cancelOrder = (id) =>
  authFetch(`/api/trading/orders/${id}`, { method: 'DELETE' }).then(json)
export const getTradingMode = () => authFetch('/api/trading/mode').then(json)

// ---- AI ----
export const aiAnalyze = (symbol) =>
  authFetch('/api/ai/analyze', { method: 'POST', body: JSON.stringify({ symbol }) }).then(json)
export const aiProvider = () => authFetch('/api/ai/provider').then(json)
export const aiTraderStart = (body = {}) =>
  authFetch('/api/ai/trader/start', { method: 'POST', body: JSON.stringify(body) }).then(json)
export const aiTraderStop = () =>
  authFetch('/api/ai/trader/stop', { method: 'POST' }).then(json)
export const aiTraderStatus = () => authFetch('/api/ai/trader/status').then(json)
export const aiDecisions = () => authFetch('/api/ai/decisions').then(json)
