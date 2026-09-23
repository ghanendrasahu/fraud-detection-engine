import React from 'react'

const severityColors = {
  LOW: 'text-gray-400',
  MEDIUM: 'text-fraud-yellow',
  HIGH: 'text-orange-400',
  CRITICAL: 'text-fraud-red',
}

export default function ReasonCodes({ codes }) {
  if (!codes || codes.length === 0) {
    return (
      <div className="bg-surface-light rounded-lg p-4 border border-surface-border">
        <h3 className="text-sm font-semibold text-gray-400 mb-2">REASON CODES</h3>
        <p className="text-sm text-gray-500">No risk factors detected</p>
      </div>
    )
  }

  return (
    <div className="bg-surface-light rounded-lg p-4 border border-surface-border">
      <h3 className="text-sm font-semibold text-gray-400 mb-3">REASON CODES</h3>
      <div className="space-y-2">
        {codes.map((rc, i) => (
          <div
            key={i}
            className="flex items-start gap-3 p-2 rounded bg-surface"
          >
            <span className={`text-lg ${severityColors[rc.severity] || 'text-gray-400'}`}>
              {rc.severity === 'CRITICAL' ? '◉' : rc.severity === 'HIGH' ? '●' : rc.severity === 'MEDIUM' ? '◐' : '○'}
            </span>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">{rc.message}</span>
                <span className={`text-xs px-1.5 py-0.5 rounded ${severityColors[rc.severity]} bg-surface-light`}>
                  {rc.severity}
                </span>
              </div>
              <p className="text-xs text-gray-500 mt-0.5">
                {rc.code} • Source: {rc.source}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
