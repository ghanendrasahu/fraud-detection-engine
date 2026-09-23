import React from 'react'

const severityColors = {
  LOW: 'bg-gray-600',
  MEDIUM: 'bg-fraud-yellow',
  HIGH: 'bg-orange-500',
  CRITICAL: 'bg-fraud-red',
}

const severityIcons = {
  LOW: '○',
  MEDIUM: '◐',
  HIGH: '●',
  CRITICAL: '◉',
}

export default function RiskBreakdown({ result }) {
  const bars = [
    { label: 'ML Risk', value: result.ml_risk_score * 100, max: 100, color: result.ml_risk_score > 0.85 ? 'bg-fraud-red' : result.ml_risk_score > 0.5 ? 'bg-fraud-yellow' : 'bg-fraud-green' },
    { label: 'Graph Risk', value: result.graph_penalty, max: 100, color: result.graph_penalty > 70 ? 'bg-fraud-red' : result.graph_penalty > 40 ? 'bg-fraud-yellow' : 'bg-fraud-green' },
    { label: 'Velocity', value: Math.min((result.features?.account_velocity_1h || 0) * 10, 100), max: 100, color: (result.features?.account_velocity_1h || 0) >= 5 ? 'bg-fraud-red' : 'bg-fraud-blue' },
    { label: 'Travel Speed', value: Math.min((result.features?.speed_kmh || 0) / 20, 100), max: 100, color: (result.features?.speed_kmh || 0) > 800 ? 'bg-fraud-red' : 'bg-fraud-blue' },
  ]

  return (
    <div className="bg-surface-light rounded-lg p-4 border border-surface-border">
      <h3 className="text-sm font-semibold text-gray-400 mb-3">RISK BREAKDOWN</h3>
      <div className="space-y-3">
        {bars.map((bar) => (
          <div key={bar.label}>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-gray-400">{bar.label}</span>
              <span className="text-white font-mono">{bar.value.toFixed(1)}%</span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-2">
              <div
                className={`${bar.color} h-2 rounded-full transition-all duration-500`}
                style={{ width: `${Math.min(bar.value, 100)}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
