import React from 'react'
import { processTransaction } from '../api'

const scenarios = [
  { id: 'normal_user', label: 'NORMAL', color: 'bg-fraud-green hover:bg-fraud-green/80' },
  { id: 'high_velocity', label: 'HIGH VELOCITY', color: 'bg-fraud-yellow hover:bg-fraud-yellow/80 text-black' },
  { id: 'new_device', label: 'NEW DEVICE', color: 'bg-fraud-blue hover:bg-fraud-blue/80' },
  { id: 'impossible_travel', label: 'IMPOSSIBLE TRAVEL', color: 'bg-orange-500 hover:bg-orange-500/80' },
  { id: 'suspicious_device', label: 'SUSPICIOUS DEVICE', color: 'bg-fraud-red hover:bg-fraud-red/80' },
  { id: 'suspicious_ip', label: 'SUSPICIOUS IP', color: 'bg-purple-500 hover:bg-purple-500/80' },
  { id: 'high_amount', label: 'HIGH AMOUNT', color: 'bg-pink-500 hover:bg-pink-500/80' },
]

const cityCoords = {
  mumbai: { lat: 19.0760, lon: 72.8777 },
  delhi: { lat: 28.7041, lon: 77.1025 },
  bangalore: { lat: 12.9716, lon: 77.5946 },
  chennai: { lat: 13.0827, lon: 80.2707 },
  kolkata: { lat: 22.5726, lon: 88.3639 },
  hyderabad: { lat: 17.3850, lon: 78.4867 },
}

const scenarioConfig = {
  normal_user: { amount: [200, 8000], device: 'device_normal_01', ip: '172.16.0.1', city: 'bangalore' },
  high_velocity: { amount: [1000, 30000], device: 'device_normal_02', ip: '172.16.0.2', city: 'mumbai' },
  new_device: { amount: [5000, 50000], device: 'device_new_unknown', ip: '10.0.0.50', city: 'delhi' },
  impossible_travel: { amount: [20000, 120000], device: 'device_normal_01', ip: '172.16.0.1', city: 'chennai' },
  suspicious_device: { amount: [30000, 200000], device: 'device_suspicious_01', ip: '10.0.0.99', city: 'kolkata' },
  suspicious_ip: { amount: [15000, 80000], device: 'device_normal_03', ip: '10.10.10.10', city: 'hyderabad' },
  high_amount: { amount: [100000, 400000], device: 'device_normal_01', ip: '172.16.0.1', city: 'bangalore' },
}

function randomBetween(min, max) {
  return Math.round((Math.random() * (max - min) + min) * 100) / 100
}

function generateTxn(scenario) {
  const cfg = scenarioConfig[scenario]
  const city = cityCoords[cfg.city]
  const amount = randomBetween(cfg.amount[0], cfg.amount[1])
  const now = new Date().toISOString()

  return {
    transaction_id: `txn_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`,
    user_id: 'user_1001',
    amount,
    timestamp: now,
    merchant_id: `merchant_${Math.floor(Math.random() * 900 + 100)}`,
    device_id: cfg.device,
    ip_address: cfg.ip,
    location_lat: city.lat + (Math.random() - 0.5) * 0.02,
    location_long: city.lon + (Math.random() - 0.5) * 0.02,
  }
}

export default function TransactionSimulator({ onResult }) {
  const [loading, setLoading] = React.useState(null)
  const [error, setError] = React.useState(null)

  const handleSimulate = async (scenarioId) => {
    setLoading(scenarioId)
    setError(null)
    try {
      const txn = generateTxn(scenarioId)
      const result = await processTransaction(txn)
      onResult(result)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(null)
    }
  }

  return (
    <div className="bg-surface-light rounded-lg p-4 border border-surface-border">
      <h3 className="text-sm font-semibold text-gray-400 mb-3">TRANSACTION SIMULATOR</h3>
      <div className="flex flex-wrap gap-2">
        {scenarios.map((s) => (
          <button
            key={s.id}
            onClick={() => handleSimulate(s.id)}
            disabled={loading !== null}
            className={`${s.color} px-3 py-1.5 rounded text-xs font-semibold text-white transition disabled:opacity-50`}
          >
            {loading === s.id ? '...' : s.label}
          </button>
        ))}
      </div>
      {error && (
        <p className="text-fraud-red text-xs mt-2">{error}</p>
      )}
    </div>
  )
}
