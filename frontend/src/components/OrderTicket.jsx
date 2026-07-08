import { useState } from 'react'
import { placeOrder } from '../api'

const INPUT = 'w-full bg-[#0b0e14] border border-gray-700 rounded px-2 py-1.5 text-sm text-gray-200'

export default function OrderTicket({ symbols, symbol, onFilled }) {
  const [form, setForm] = useState({ side: 'buy', qty: 10, order_type: 'market', limit_price: '' })
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true); setError(null); setResult(null)
    try {
      const body = {
        symbol,
        side: form.side,
        qty: Number(form.qty),
        order_type: form.order_type,
        ...(form.order_type === 'limit' ? { limit_price: Number(form.limit_price) } : {}),
      }
      const res = await placeOrder(body)
      setResult(res)
      onFilled?.()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const status = result?.order?.status

  return (
    <form onSubmit={submit} className="space-y-2 text-sm">
      <div className="grid grid-cols-2 gap-2">
        {['buy', 'sell'].map((s) => (
          <button type="button" key={s} onClick={() => setForm({ ...form, side: s })}
            className={`rounded py-1.5 font-medium capitalize ${
              form.side === s
                ? s === 'buy' ? 'bg-emerald-600 text-white' : 'bg-red-600 text-white'
                : 'border border-gray-700 text-gray-400'
            }`}>
            {s}
          </button>
        ))}
      </div>
      <div className="grid grid-cols-2 gap-2">
        <label className="block">
          <span className="text-xs text-gray-500">Qty</span>
          <input className={INPUT} type="number" min="1" value={form.qty}
                 onChange={(e) => setForm({ ...form, qty: e.target.value })} />
        </label>
        <label className="block">
          <span className="text-xs text-gray-500">Type</span>
          <select className={INPUT} value={form.order_type}
                  onChange={(e) => setForm({ ...form, order_type: e.target.value })}>
            <option value="market">Market</option>
            <option value="limit">Limit</option>
          </select>
        </label>
      </div>
      {form.order_type === 'limit' && (
        <label className="block">
          <span className="text-xs text-gray-500">Limit price</span>
          <input className={INPUT} type="number" step="0.05" min="0" required
                 value={form.limit_price}
                 onChange={(e) => setForm({ ...form, limit_price: e.target.value })} />
        </label>
      )}
      <button disabled={busy}
        className={`w-full rounded py-1.5 text-sm font-medium text-white disabled:opacity-50 ${
          form.side === 'buy' ? 'bg-emerald-600 hover:bg-emerald-500' : 'bg-red-600 hover:bg-red-500'
        }`}>
        {busy ? 'Placing…' : `${form.side === 'buy' ? 'Buy' : 'Sell'} ${symbol}`}
      </button>

      {result && (
        <p className={`text-xs ${status === 'filled' ? 'text-emerald-400'
                       : status === 'rejected' ? 'text-red-400' : 'text-amber-400'}`}>
          {status === 'filled' && `Filled ${result.fill.qty} @ ${result.fill.price} (fee ${result.fill.commission})`}
          {status === 'open' && 'Resting on the book (fills when price crosses your limit)'}
          {status === 'rejected' && `Rejected — ${result.order.reason}`}
          {result.order.reason?.includes('resized') && ` · ${result.order.reason}`}
        </p>
      )}
      {error && <p className="text-xs text-red-400">{error}</p>}
    </form>
  )
}
