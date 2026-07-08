import { useEffect, useState } from 'react'
import { aiAnalyze, aiDecisions, aiProvider, aiTraderStart, aiTraderStatus, aiTraderStop } from '../api'

const ACTION_CLS = { buy: 'text-emerald-400', sell: 'text-red-400', hold: 'text-gray-300' }

export default function AIPanel({ symbol, onTraded }) {
  const [analysis, setAnalysis] = useState(null)
  const [busy, setBusy] = useState(false)
  const [provider, setProvider] = useState(null)
  const [trader, setTrader] = useState({ running: false })
  const [log, setLog] = useState([])
  const [error, setError] = useState(null)

  const refresh = async () => {
    try {
      const [st, dec] = await Promise.all([aiTraderStatus(), aiDecisions()])
      setTrader(st)
      setLog(dec.decisions || [])
      if (st.running) onTraded?.()
    } catch { /* not fatal */ }
  }

  useEffect(() => {
    aiProvider().then(setProvider).catch(() => {})
    refresh()
    const t = setInterval(refresh, 4000)
    return () => clearInterval(t)
  }, [])

  const analyze = async () => {
    setBusy(true); setError(null)
    try { setAnalysis(await aiAnalyze(symbol)) } catch (e) { setError(e.message) }
    setBusy(false)
  }

  const toggleTrader = async () => {
    setError(null)
    try {
      if (trader.running) await aiTraderStop()
      else await aiTraderStart({ interval: 5, min_confidence: 0.5 })
      refresh()
    } catch (e) { setError(e.message) }
  }

  return (
    <div className="space-y-3 text-sm">
      <div className="flex items-center justify-between">
        <span className="text-[11px] text-gray-500">
          engine: {provider ? provider.provider : '…'}
        </span>
        <button onClick={analyze} disabled={busy}
          className="rounded bg-purple-600 px-3 py-1 text-xs font-medium text-white hover:bg-purple-500 disabled:opacity-50">
          {busy ? 'Analyzing…' : `Analyze ${symbol}`}
        </button>
      </div>

      {analysis && !analysis.error && (
        <div className="rounded bg-[#0b0e14] p-3">
          <div className="mb-1 flex items-center gap-2">
            <span className={`text-base font-semibold uppercase ${ACTION_CLS[analysis.action]}`}>
              {analysis.action}
            </span>
            <span className="text-xs text-gray-500">confidence {(analysis.confidence * 100).toFixed(0)}%</span>
            <span className="ml-auto text-[10px] text-gray-600">{analysis.provider}</span>
          </div>
          <p className="text-xs leading-relaxed text-gray-300">{analysis.rationale}</p>
          {analysis.risks && <p className="mt-1 text-[11px] text-amber-400/80">⚠ {analysis.risks}</p>}
        </div>
      )}
      {analysis?.error && <p className="text-xs text-red-400">{analysis.error}</p>}

      <div className="rounded bg-[#0b0e14] p-3">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm text-gray-200">AI auto-trader</div>
            <div className="text-[11px] text-gray-500">
              {trader.running
                ? `running · ${trader.symbols?.join(', ')} · every ${trader.interval}s`
                : 'paper mode · risk-gated · long-only'}
            </div>
          </div>
          <button onClick={toggleTrader}
            className={`rounded px-3 py-1.5 text-xs font-medium text-white ${
              trader.running ? 'bg-red-600 hover:bg-red-500' : 'bg-emerald-600 hover:bg-emerald-500'
            }`}>
            {trader.running ? 'Stop' : 'Start'}
          </button>
        </div>
      </div>

      {log.length > 0 && (
        <div className="max-h-56 overflow-y-auto rounded bg-[#0b0e14] p-2">
          {log.map((d, i) => (
            <div key={i} className="border-b border-gray-800/60 py-1.5 last:border-0">
              <div className="flex items-center gap-2 text-[11px]">
                <span className="font-mono text-gray-600">{d.time.slice(11, 19)}</span>
                <span className="text-gray-300">{d.symbol}</span>
                <span className={`font-semibold uppercase ${ACTION_CLS[d.action]}`}>{d.action}</span>
                <span className="text-gray-500">{(d.confidence * 100).toFixed(0)}%</span>
                {d.order_id && <span className="text-emerald-500">● order</span>}
              </div>
              <p className="text-[11px] leading-snug text-gray-500">{d.rationale}</p>
            </div>
          ))}
        </div>
      )}
      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  )
}
