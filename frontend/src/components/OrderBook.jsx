// Order-book depth ladder from the live WS snapshot.
function Row({ px, qty, side, max }) {
  const isBid = side === 'bid'
  return (
    <div className="relative flex justify-between px-2 py-0.5 font-mono text-xs">
      <div
        className={`absolute inset-y-0 ${isBid ? 'right-0 bg-emerald-500/15' : 'left-0 bg-red-500/15'}`}
        style={{ width: `${(qty / max) * 100}%` }}
      />
      <span className={`relative ${isBid ? 'text-emerald-400' : 'text-red-400'}`}>{px.toFixed(2)}</span>
      <span className="relative text-gray-300">{qty}</span>
    </div>
  )
}

export default function OrderBook({ message }) {
  if (!message) return <div className="text-sm text-gray-500">waiting for ticks…</div>
  const max = Math.max(...message.bids.map((b) => b[1]), ...message.asks.map((a) => a[1]), 1)
  return (
    <div>
      {message.asks.slice().reverse().map((a, i) => (
        <Row key={`a${i}`} px={a[0]} qty={a[1]} side="ask" max={max} />
      ))}
      <div className="border-y border-gray-700 py-1 text-center font-mono text-sm text-gray-100">
        {message.price.toFixed(2)}
      </div>
      {message.bids.map((b, i) => (
        <Row key={`b${i}`} px={b[0]} qty={b[1]} side="bid" max={max} />
      ))}
    </div>
  )
}
