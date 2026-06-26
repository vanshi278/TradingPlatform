import { useState } from 'react'
import { runBacktest } from '../api'

const INPUT = 'w-full bg-[#0b0e14] border border-gray-700 rounded px-2 py-1 text-sm text-gray-200'

export default function BacktestForm({ onResult }) {
  const [form, setForm] = useState({
    symbols: 'RELIANCE', strategy: 'ma',
    start: '2018-01-01', end: '2024-01-01', execution: 'fixed',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const upd = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    setLoading(true); setError(null)
    try {
      const d = await runBacktest(form)
      if (d.error) setError(d.error)
      else onResult(d)
    } catch (err) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={submit} className="space-y-2 text-sm">
      <label className="block">
        <span className="text-xs text-gray-500">Symbols</span>
        <input className={INPUT} value={form.symbols} onChange={upd('symbols')} placeholder="RELIANCE,TCS" />
      </label>
      <label className="block">
        <span className="text-xs text-gray-500">Strategy</span>
        <select className={INPUT} value={form.strategy} onChange={upd('strategy')}>
          <option value="buyhold">Buy &amp; hold</option>
          <option value="ma">MA crossover</option>
          <option value="pairs">Pairs (2 symbols)</option>
          <option value="crosssec">X-sec momentum</option>
        </select>
      </label>
      <div className="grid grid-cols-2 gap-2">
        <label className="block">
          <span className="text-xs text-gray-500">Start</span>
          <input className={INPUT} value={form.start} onChange={upd('start')} />
        </label>
        <label className="block">
          <span className="text-xs text-gray-500">End</span>
          <input className={INPUT} value={form.end} onChange={upd('end')} />
        </label>
      </div>
      <label className="block">
        <span className="text-xs text-gray-500">Execution</span>
        <select className={INPUT} value={form.execution} onChange={upd('execution')}>
          <option value="fixed">Fixed slippage</option>
          <option value="impact">Square-root impact</option>
        </select>
      </label>
      <button
        disabled={loading}
        className="w-full rounded bg-blue-600 py-1.5 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50"
      >
        {loading ? 'Running…' : 'Run backtest'}
      </button>
      {error && <p className="text-xs text-red-400">{error}</p>}
    </form>
  )
}
