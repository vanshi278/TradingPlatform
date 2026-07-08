const inr = (x) => (x == null ? '—' : `₹${Number(x).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`)
const pnlCls = (v) => (v >= 0 ? 'text-emerald-400' : 'text-red-400')

export default function PortfolioPanel({ portfolio }) {
  if (!portfolio) return <p className="text-sm text-gray-500">loading…</p>
  const cells = [
    ['Equity', inr(portfolio.equity), 'text-white'],
    ['Cash', inr(portfolio.cash), 'text-gray-200'],
    ['Total P&L', inr(portfolio.total_pnl), pnlCls(portfolio.total_pnl)],
    ['Unrealized', inr(portfolio.unrealized_pnl), pnlCls(portfolio.unrealized_pnl)],
  ]
  return (
    <div>
      <div className="mb-3 grid grid-cols-2 gap-2 lg:grid-cols-4">
        {cells.map(([k, v, cls]) => (
          <div key={k} className="rounded bg-[#0b0e14] px-3 py-2">
            <div className="text-[11px] text-gray-500">{k}</div>
            <div className={`text-lg ${cls}`}>{v}</div>
          </div>
        ))}
      </div>
      {portfolio.positions.length === 0 ? (
        <p className="text-sm text-gray-500">flat — no open positions</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-[11px] text-gray-500">
              <th className="font-normal">Symbol</th>
              <th className="text-right font-normal">Qty</th>
              <th className="text-right font-normal">Avg cost</th>
              <th className="text-right font-normal">Mark</th>
              <th className="text-right font-normal">Unrealized</th>
            </tr>
          </thead>
          <tbody>
            {portfolio.positions.map((p) => (
              <tr key={p.symbol} className="border-t border-gray-800/60">
                <td className="py-1 text-gray-200">{p.symbol}</td>
                <td className={`text-right font-mono ${p.qty >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>{p.qty}</td>
                <td className="text-right font-mono text-gray-300">{p.avg_cost.toFixed(2)}</td>
                <td className="text-right font-mono text-gray-300">{p.mark.toFixed(2)}</td>
                <td className={`text-right font-mono ${pnlCls(p.unrealized_pnl)}`}>
                  {p.unrealized_pnl >= 0 ? '+' : ''}{p.unrealized_pnl.toFixed(0)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
