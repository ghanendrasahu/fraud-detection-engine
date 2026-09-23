import React from 'react'
import Header from './components/Header'
import TransactionCard from './components/TransactionCard'
import RiskBreakdown from './components/RiskBreakdown'
import ReasonCodes from './components/ReasonCodes'
import InvestigationGraph from './components/InvestigationGraph'
import TransactionSimulator from './components/TransactionSimulator'

export default function App() {
  const [latestResult, setLatestResult] = React.useState(null)
  const [history, setHistory] = React.useState([])

  const handleResult = (result) => {
    setLatestResult(result)
    setHistory((prev) => [result, ...prev].slice(0, 20))
  }

  return (
    <div className="min-h-screen bg-surface text-white">
      <Header result={latestResult} />
      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <TransactionSimulator onResult={handleResult} />
            {latestResult && (
              <>
                <TransactionCard result={latestResult} />
                <RiskBreakdown result={latestResult} />
                <ReasonCodes codes={latestResult.reason_codes} />
                {latestResult.investigator_summary && (
                  <div className="bg-surface-light rounded-lg p-4 border border-surface-border">
                    <h3 className="text-sm font-semibold text-gray-400 mb-2">AI INVESTIGATOR SUMMARY</h3>
                    <p className="text-sm text-gray-300">{latestResult.investigator_summary}</p>
                  </div>
                )}
              </>
            )}
          </div>
          <div className="space-y-6">
            <InvestigationGraph graph={latestResult?.graph} />
            {history.length > 0 && (
              <div className="bg-surface-light rounded-lg p-4 border border-surface-border">
                <h3 className="text-sm font-semibold text-gray-400 mb-3">RECENT TRANSACTIONS</h3>
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {history.map((h) => (
                    <div
                      key={h.transaction_id}
                      className="flex items-center justify-between text-xs p-2 rounded bg-surface"
                    >
                      <span className="text-gray-400 truncate">{h.transaction_id}</span>
                      <span
                        className={
                          h.decision === 'INVESTIGATION_REQUIRED'
                            ? 'text-fraud-red font-bold'
                            : 'text-fraud-green font-bold'
                        }
                      >
                        {(h.ml_risk_score * 100).toFixed(1)}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
