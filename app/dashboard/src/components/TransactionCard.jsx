import React from 'react'

export default function TransactionCard({ result }) {
  const txn = result
  return (
    <div className="bg-surface-light rounded-lg p-4 border border-surface-border">
      <h3 className="text-sm font-semibold text-gray-400 mb-3">TRANSACTION DETAILS</h3>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div>
          <p className="text-xs text-gray-500">Transaction ID</p>
          <p className="text-sm font-mono">{txn.transaction_id}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">User ID</p>
          <p className="text-sm">{txn.features?.user_id || 'N/A'}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Amount</p>
          <p className="text-sm font-bold">₹{txn.features?.amount_sum_24h?.toLocaleString('en-IN') || '0'}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">New Device</p>
          <p className={`text-sm font-bold ${txn.features?.is_new_device ? 'text-fraud-yellow' : 'text-fraud-green'}`}>
            {txn.features?.is_new_device ? 'YES' : 'NO'}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Velocity (1h)</p>
          <p className="text-sm">{txn.features?.account_velocity_1h || 0}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Travel Speed</p>
          <p className={`text-sm ${txn.features?.speed_kmh > 800 ? 'text-fraud-red font-bold' : ''}`}>
            {txn.features?.speed_kmh?.toLocaleString('en-IN') || '0'} km/h
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Graph Penalty</p>
          <p className={`text-sm ${txn.graph_penalty > 70 ? 'text-fraud-red font-bold' : ''}`}>
            {txn.graph_penalty}/100
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500">ML Risk Score</p>
          <p className={`text-sm font-bold ${txn.ml_risk_score > 0.85 ? 'text-fraud-red' : txn.ml_risk_score > 0.5 ? 'text-fraud-yellow' : 'text-fraud-green'}`}>
            {(txn.ml_risk_score * 100).toFixed(1)}%
          </p>
        </div>
      </div>
    </div>
  )
}
