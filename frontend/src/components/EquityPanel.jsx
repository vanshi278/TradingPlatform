import { useEffect, useRef } from 'react'
import { createChart } from 'lightweight-charts'

// Equity curve (× initial capital) from the latest backtest result.
export default function EquityPanel({ result }) {
  const elRef = useRef(null)
  const objs = useRef(null)

  useEffect(() => {
    const chart = createChart(elRef.current, {
      height: 260,
      layout: { background: { color: 'transparent' }, textColor: '#9ca3af' },
      grid: {
        vertLines: { color: 'rgba(128,128,128,0.08)' },
        horzLines: { color: 'rgba(128,128,128,0.08)' },
      },
      rightPriceScale: { borderColor: 'rgba(128,128,128,0.2)' },
      timeScale: { borderColor: 'rgba(128,128,128,0.2)' },
    })
    const area = chart.addAreaSeries({
      lineColor: '#378add', topColor: 'rgba(55,138,221,0.4)',
      bottomColor: 'rgba(55,138,221,0.02)', lineWidth: 2,
    })
    objs.current = { chart, area }
    const ro = new ResizeObserver(() => chart.applyOptions({ width: elRef.current.clientWidth }))
    ro.observe(elRef.current)
    chart.applyOptions({ width: elRef.current.clientWidth })
    return () => { ro.disconnect(); chart.remove() }
  }, [])

  useEffect(() => {
    if (!result?.equity || !objs.current) return
    objs.current.area.setData(result.equity)
    objs.current.chart.timeScale().fitContent()
  }, [result])

  return (
    <div>
      {!result && <p className="mb-2 text-sm text-gray-500">run a backtest to see the equity curve →</p>}
      <div ref={elRef} className="w-full" />
    </div>
  )
}
