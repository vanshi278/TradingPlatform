export default function PositionsTable({ result }) {
  if (!result) return <p className="text-sm text-gray-500">—</p>
  const positions = result.positions || []
  if (!positions.length) return <p className="text-sm text-gray-500">flat (no open positions)</p>
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-xs text-gray-500">
          <th className="text-left font-normal">Symbol</th>
          <th className="text-right font-normal">Shares</th>
        </tr>
      </thead>
      <tbody>
        {positions.map((p) => (
          <tr key={p.symbol}>
            <td className="py-0.5 text-gray-200">{p.symbol}</td>
            <td className={`text-right font-mono ${p.shares >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              {p.shares}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
