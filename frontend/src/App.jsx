import { useEffect, useState } from 'react'
import { marketSocket } from './api'
import BacktestForm from './components/BacktestForm'
import EquityPanel from './components/EquityPanel'
import OrderBook from './components/OrderBook'
import PositionsTable from './components/PositionsTable'
import PriceChart from './components/PriceChart'
import RiskPanel from './components/RiskPanel'

const pct = (x) => (x == null ? '—' : `${(x * 100).toFixed(1)}%`)

function Card({ title, children, className = '' }) {
  return (
    <div className={`rounded-lg border border-gray-800 bg-[#11151c] ${className}`}>
      {title && (
        <div className="border-b border-gray-800 px-4 py-2 text-sm font-medium text-gray-300">{title}</div>
      )}
      <div className="p-4">{children}</div>
    </div>
  )
}

function Metrics({ result }) {
  if (!result?.metrics) return <p className="text-sm text-gray-500">run a backtest →</p>
  const m = result.metrics
  const cells = [
    ['Total return', pct(m.total_return)],
    ['CAGR', pct(m.cagr)],
    ['Sharpe', m.sharpe?.toFixed(2)],
    ['Max DD', pct(m.max_drawdown)],
    ['Trades', result.trades],
    ['Periods', m.n_periods],
  ]
  return (
    <div className="grid grid-cols-2 gap-2">
      {cells.map(([k, v]) => (
        <div key={k} className="rounded bg-[#0b0e14] px-3 py-2">
          <div className="text-[11px] text-gray-500">{k}</div>
          <div className="text-lg text-white">{v ?? '—'}</div>
        </div>
      ))}
    </div>
  )
}

export default function App() {
  const [msg, setMsg] = useState(null)
  const [connected, setConnected] = useState(false)
  const [result, setResult] = useState(null)

  useEffect(() => {
    let ws
    let alive = true
    let retry
    const connect = () => {
      ws = marketSocket()
      ws.onopen = () => setConnected(true)
      ws.onmessage = (e) => setMsg(JSON.parse(e.data))
      ws.onclose = () => {
        setConnected(false)
        if (alive) retry = setTimeout(connect, 1500)
      }
    }
    connect()
    return () => { alive = false; clearTimeout(retry); if (ws) ws.close() }
  }, [])

  return (
    <div className="mx-auto max-w-7xl px-6 py-5">
      <header className="mb-5 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">AlphaForge</h1>
          <p className="text-xs text-gray-500">Systematic Trading &amp; Research Platform</p>
        </div>
        <span
          className={`rounded px-2 py-1 text-xs ${
            connected ? 'bg-emerald-500/15 text-emerald-400' : 'bg-red-500/15 text-red-400'
          }`}
        >
          {connected ? '● live' : '○ disconnected'} · {msg?.symbol || '—'}
        </span>
      </header>

      <div className="mb-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card title="Live price" className="lg:col-span-2">
          <PriceChart message={msg} />
        </Card>
        <Card title="Order book">
          <OrderBook message={msg} />
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card title="Backtest runner">
          <BacktestForm onResult={setResult} />
        </Card>
        <Card title="Equity curve" className="lg:col-span-2">
          <EquityPanel result={result} />
        </Card>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card title="Performance">
          <Metrics result={result} />
        </Card>
        <Card title="Positions">
          <PositionsTable result={result} />
        </Card>
        <Card title="Risk">
          <RiskPanel result={result} />
        </Card>
      </div>
    </div>
  )
}
