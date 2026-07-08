import { cancelOrder } from '../api'

const CHIP = {
  filled: 'bg-emerald-500/15 text-emerald-400',
  open: 'bg-amber-500/15 text-amber-400',
  cancelled: 'bg-gray-500/15 text-gray-400',
  rejected: 'bg-red-500/15 text-red-400',
}

export default function Blotter({ orders, onChanged }) {
  if (!orders) return <p className="text-sm text-gray-500">loading…</p>
  if (!orders.length) return <p className="text-sm text-gray-500">no orders yet — place one →</p>

  const cancel = async (id) => {
    try { await cancelOrder(id); onChanged?.() } catch { /* surfaced via refresh */ }
  }

  return (
    <div className="max-h-64 overflow-y-auto">
      <table className="w-full text-sm">
        <thead className="sticky top-0 bg-[#11151c]">
          <tr className="text-left text-[11px] text-gray-500">
            <th className="font-normal">Time</th>
            <th className="font-normal">Symbol</th>
            <th className="font-normal">Side</th>
            <th className="text-right font-normal">Qty</th>
            <th className="font-normal">Type</th>
            <th className="font-normal">Src</th>
            <th className="font-normal">Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {orders.map((o) => (
            <tr key={o.id} className="border-t border-gray-800/60" title={o.reason || ''}>
              <td className="py-1 font-mono text-[11px] text-gray-500">{o.created_at.slice(11, 19)}</td>
              <td className="text-gray-200">{o.symbol}</td>
              <td className={o.side === 'buy' ? 'text-emerald-400' : 'text-red-400'}>{o.side}</td>
              <td className="text-right font-mono text-gray-300">{o.qty}</td>
              <td className="text-gray-400">{o.order_type}{o.limit_price ? ` @${o.limit_price}` : ''}</td>
              <td className="text-gray-400">{o.source === 'ai' ? '🤖' : '👤'}</td>
              <td><span className={`rounded px-1.5 py-0.5 text-[11px] ${CHIP[o.status] || ''}`}>{o.status}</span></td>
              <td className="text-right">
                {o.status === 'open' && (
                  <button onClick={() => cancel(o.id)}
                          className="text-[11px] text-gray-400 underline hover:text-red-400">
                    cancel
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
