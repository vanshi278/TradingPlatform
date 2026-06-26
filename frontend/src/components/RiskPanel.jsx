const money = (x) => (x == null ? '—' : `$${Math.round(x).toLocaleString()}`)
const pct = (x) => (x == null ? '—' : `${(x * 100).toFixed(1)}%`)

function Row({ k, v }) {
  return (
    <div className="flex justify-between">
      <span className="text-gray-400">{k}</span>
      <span className="font-mono text-gray-100">{v}</span>
    </div>
  )
}

export default function RiskPanel({ result }) {
  if (!result?.risk) return <p className="text-sm text-gray-500">—</p>
  const r = result.risk
  return (
    <div className="space-y-2 text-sm">
      <Row k="99% VaR (hist)" v={money(r.var_99)} />
      <Row k="99% VaR (param)" v={money(r.var_param_99)} />
      <Row k="Max drawdown" v={pct(r.max_drawdown)} />
      <div className="flex items-center justify-between pt-1">
        <span className="text-gray-400">Kill switch</span>
        <span
          className={`rounded px-2 py-0.5 text-xs ${
            r.kill_switch ? 'bg-red-500/15 text-red-400' : 'bg-emerald-500/15 text-emerald-400'
          }`}
        >
          {r.kill_switch ? 'TRIPPED (−25%)' : 'armed'}
        </span>
      </div>
    </div>
  )
}
