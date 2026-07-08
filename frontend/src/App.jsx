import { useCallback, useEffect, useRef, useState } from 'react'
import { getOrders, getPortfolio, getSymbols, getTradingMode, marketSocket } from './api'
import { useAuth } from './auth'
import AIPanel from './components/AIPanel'
import AuthPage from './components/AuthPage'
import BacktestForm from './components/BacktestForm'
import Blotter from './components/Blotter'
import EquityPanel from './components/EquityPanel'
import OrderBook from './components/OrderBook'
import OrderTicket from './components/OrderTicket'
import PortfolioPanel from './components/PortfolioPanel'
import PriceChart from './components/PriceChart'
import RiskPanel from './components/RiskPanel'

const pct = (x) => (x == null ? '—' : `${(x * 100).toFixed(1)}%`)

function Card({ title, right, children, className = '' }) {
  return (
    <div className={`rounded-lg border border-gray-800 bg-[#11151c] ${className}`}>
      {title && (
        <div className="flex items-center justify-between border-b border-gray-800 px-4 py-2">
          <span className="text-sm font-medium text-gray-300">{title}</span>
          {right}
        </div>
      )}
      <div className="p-4">{children}</div>
    </div>
  )
}

function Metrics({ result }) {
  if (!result?.metrics) return <p className="text-sm text-gray-500">run a backtest →</p>
  const m = result.metrics
  const cells = [
    ['Total return', pct(m.total_return)], ['CAGR', pct(m.cagr)],
    ['Sharpe', m.sharpe?.toFixed(2)], ['Max DD', pct(m.max_drawdown)],
    ['Trades', result.trades], ['Periods', m.n_periods],
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

function Dashboard() {
  const { email, logout } = useAuth()
  const [symbols, setSymbols] = useState(['RELIANCE'])
  const [symbol, setSymbol] = useState('RELIANCE')
  const [msg, setMsg] = useState(null)
  const [connected, setConnected] = useState(false)
  const [mode, setMode] = useState('paper')
  const [portfolio, setPortfolio] = useState(null)
  const [orders, setOrders] = useState(null)
  const [result, setResult] = useState(null)
  const wsRef = useRef(null)

  const refreshTrading = useCallback(() => {
    getPortfolio().then(setPortfolio).catch(() => {})
    getOrders().then((d) => setOrders(d.orders)).catch(() => {})
  }, [])

  useEffect(() => {
    getSymbols().then((d) => setSymbols(d.symbols)).catch(() => {})
    getTradingMode().then((d) => setMode(d.mode)).catch(() => {})
    refreshTrading()
    const t = setInterval(refreshTrading, 3000)
    return () => clearInterval(t)
  }, [refreshTrading])

  useEffect(() => {
    let ws, retry, alive = true
    const connect = () => {
      ws = marketSocket(symbol)
      wsRef.current = ws
      ws.onopen = () => setConnected(true)
      ws.onmessage = (e) => setMsg(JSON.parse(e.data))
      ws.onclose = () => { setConnected(false); if (alive) retry = setTimeout(connect, 1500) }
    }
    connect()
    return () => { alive = false; clearTimeout(retry); ws?.close() }
  }, [])           // one socket; symbol switches via message below

  const switchSymbol = (s) => {
    setSymbol(s)
    if (wsRef.current?.readyState === 1) wsRef.current.send(JSON.stringify({ symbol: s }))
  }

  return (
    <div className="mx-auto max-w-7xl px-6 py-5">
      <header className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-white">AlphaForge</h1>
          <p className="text-xs text-gray-500">Systematic Trading &amp; Research Platform</p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`rounded px-2 py-1 text-xs uppercase ${
            mode === 'live' ? 'bg-red-500/15 text-red-400' : 'bg-blue-500/15 text-blue-400'
          }`}>{mode}</span>
          <span className={`rounded px-2 py-1 text-xs ${
            connected ? 'bg-emerald-500/15 text-emerald-400' : 'bg-red-500/15 text-red-400'
          }`}>{connected ? '● live' : '○ disconnected'}</span>
          <span className="text-xs text-gray-500">{email}</span>
          <button onClick={logout}
                  className="rounded border border-gray-700 px-2 py-1 text-xs text-gray-400 hover:text-gray-200">
            Log out
          </button>
        </div>
      </header>

      <div className="mb-4 flex flex-wrap gap-1.5">
        {symbols.map((s) => (
          <button key={s} onClick={() => switchSymbol(s)}
            className={`rounded px-3 py-1 text-xs font-medium ${
              s === symbol ? 'bg-blue-600 text-white' : 'border border-gray-800 text-gray-400 hover:text-gray-200'
            }`}>
            {s}
            {msg?.prices?.[s] != null && <span className="ml-1.5 font-mono">{msg.prices[s]}</span>}
          </button>
        ))}
      </div>

      <div className="mb-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card title={`Live price — ${symbol}`} className="lg:col-span-2"
              right={msg && <span className="font-mono text-sm text-gray-200">{msg.price?.toFixed(2)}</span>}>
          <PriceChart key={symbol} message={msg?.symbol === symbol ? msg : null} />
        </Card>
        <Card title="Order book">
          <OrderBook message={msg?.symbol === symbol ? msg : null} />
        </Card>
      </div>

      <div className="mb-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card title={`Order ticket — ${symbol}`}>
          <OrderTicket symbols={symbols} symbol={symbol} onFilled={refreshTrading} />
        </Card>
        <Card title="Portfolio (paper)" className="lg:col-span-2">
          <PortfolioPanel portfolio={portfolio} />
        </Card>
      </div>

      <div className="mb-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card title="Orders" className="lg:col-span-2">
          <Blotter orders={orders} onChanged={refreshTrading} />
        </Card>
        <Card title="AI analyst & auto-trader">
          <AIPanel symbol={symbol} onTraded={refreshTrading} />
        </Card>
      </div>

      <h2 className="mb-3 mt-8 text-sm font-semibold uppercase tracking-wider text-gray-500">
        Research — historical backtesting
      </h2>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card title="Backtest runner"><BacktestForm onResult={setResult} /></Card>
        <Card title="Equity curve" className="lg:col-span-2"><EquityPanel result={result} /></Card>
      </div>
      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card title="Performance"><Metrics result={result} /></Card>
        <Card title="Backtest risk" className="lg:col-span-2"><RiskPanel result={result} /></Card>
      </div>
    </div>
  )
}

export default function App() {
  const { authed } = useAuth()
  return authed ? <Dashboard /> : <AuthPage />
}
