import React from 'react'

export default function Header({ result }) {
  return (
    <header className="bg-surface-light border-b border-surface-border px-6 py-4">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight">
            <span className="text-fraud-blue">FRAUD</span> DETECTION ENGINE
          </h1>
          <p className="text-xs text-gray-400 mt-0.5">Real-Time Transaction Investigation Platform</p>
        </div>
        {result && (
          <div className="flex items-center gap-6">
            <div className="text-right">
              <p className="text-xs text-gray-400">AMOUNT</p>
              <p className="text-lg font-bold">
                ₹{result.features?.amount_sum_24h?.toLocaleString('en-IN') || '0'}
              </p>
            </div>
            <div className="text-right">
              <p className="text-xs text-gray-400">RISK</p>
              <p className={`text-lg font-bold ${result.ml_risk_score > 0.5 ? 'text-fraud-red' : 'text-fraud-green'}`}>
                {(result.ml_risk_score * 100).toFixed(1)}%
              </p>
            </div>
            <div className="text-right">
              <p className="text-xs text-gray-400">STATUS</p>
              <span
                className={
                  result.decision === 'INVESTIGATION_REQUIRED'
                    ? 'bg-fraud-red/20 text-fraud-red px-2 py-1 rounded text-sm font-bold'
                    : 'bg-fraud-green/20 text-fraud-green px-2 py-1 rounded text-sm font-bold'
                }
              >
                {result.decision === 'INVESTIGATION_REQUIRED' ? 'INVESTIGATION REQUIRED' : 'APPROVED'}
              </span>
            </div>
          </div>
        )}
      </div>
    </header>
  )
}
