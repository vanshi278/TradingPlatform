import { useEffect, useRef } from 'react'
import { createChart } from 'lightweight-charts'

// Live candlestick chart, aggregating the WS price stream into 2-second candles.
export default function PriceChart({ message }) {
  const elRef = useRef(null)
  const seriesRef = useRef(null)
  const candleRef = useRef(null)

  useEffect(() => {
    const chart = createChart(elRef.current, {
      height: 300,
      layout: { background: { color: 'transparent' }, textColor: '#9ca3af' },
      grid: {
        vertLines: { color: 'rgba(128,128,128,0.08)' },
        horzLines: { color: 'rgba(128,128,128,0.08)' },
      },
      timeScale: { timeVisible: true, secondsVisible: true, borderColor: 'rgba(128,128,128,0.2)' },
      rightPriceScale: { borderColor: 'rgba(128,128,128,0.2)' },
    })
    seriesRef.current = chart.addCandlestickSeries({
      upColor: '#1d9e75', downColor: '#e24b4a', borderVisible: false,
      wickUpColor: '#1d9e75', wickDownColor: '#e24b4a',
    })
    const ro = new ResizeObserver(() => chart.applyOptions({ width: elRef.current.clientWidth }))
    ro.observe(elRef.current)
    chart.applyOptions({ width: elRef.current.clientWidth })
    return () => { ro.disconnect(); chart.remove() }
  }, [])

  useEffect(() => {
    if (!message || !seriesRef.current) return
    const bucket = Math.floor(message.ts / 2) * 2
    const px = message.price
    const cur = candleRef.current
    if (!cur || cur.time !== bucket) {
      candleRef.current = { time: bucket, open: px, high: px, low: px, close: px }
    } else {
      cur.high = Math.max(cur.high, px)
      cur.low = Math.min(cur.low, px)
      cur.close = px
    }
    seriesRef.current.update(candleRef.current)
  }, [message])

  return <div ref={elRef} className="w-full" />
}
