import { useState, useEffect } from 'react'
import './Portfolio.css'

export default function Portfolio({ regime, deployment }) {
  const [allocationData, setAllocationData] = useState({
    risky: 0,
    safe: 0,
    cash: 0
  })

  useEffect(() => {
    // Use deployment data if available (after initial deploy), otherwise use rebalance data
    let allocationDollars = null
    let portfolio_value = 100000

    if (deployment?.allocation) {
      allocationDollars = deployment.allocation
      portfolio_value = deployment.portfolio_value || 100000
    } else if (regime?.rebalance?.allocation) {
      allocationDollars = regime.rebalance.allocation
      portfolio_value = regime.rebalance.portfolio_value || 100000
    }

    if (allocationDollars && portfolio_value > 0) {
      const btc = allocationDollars['BTC-USD'] || 0
      const eth = allocationDollars['ETH-USD'] || 0
      const gld = allocationDollars['GLD'] || 0
      const usd = allocationDollars['USD'] || 0
      
      setAllocationData({
        risky: Math.round(((btc + eth) * 100) / portfolio_value),
        safe: Math.round((gld * 100) / portfolio_value),
        cash: Math.round((usd * 100) / portfolio_value)
      })
    }
  }, [deployment, regime])

  const getAssets = () => {
    let allocationDollars = {}
    let portfolio_value = 100000

    if (deployment?.allocation) {
      allocationDollars = deployment.allocation
      portfolio_value = deployment.portfolio_value || 100000
    } else if (regime?.rebalance?.allocation) {
      allocationDollars = regime.rebalance.allocation
      portfolio_value = regime.rebalance.portfolio_value || 100000
    }

    return [
      { symbol: 'BTC-USD', name: 'Bitcoin', type: 'Risky', value: allocationDollars['BTC-USD'] || 0, color: '#f7931a' },
      { symbol: 'ETH-USD', name: 'Ethereum', type: 'Risky', value: allocationDollars['ETH-USD'] || 0, color: '#627eea' },
      { symbol: 'GLD', name: 'Gold ETF', type: 'Safe', value: allocationDollars['GLD'] || 0, color: '#fbbf24' },
      { symbol: 'USD', name: 'Cash (USD)', type: 'Cash', value: allocationDollars['USD'] || 0, color: '#6b7280' }
    ]
  }

  const assets = getAssets()
  const totalValue = deployment?.portfolio_value || regime?.rebalance?.portfolio_value || 100000

  return (
    <div className="portfolio-container">
      <h2>Portfolio Composition</h2>
      
      <div className="portfolio-layout">
        {/* Pie Chart */}
        <div className="pie-section">
          <div className="pie-chart">
            <svg viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="45" fill="none" stroke="#e0e0e0" strokeWidth="10"/>
              
              {/* Risky (Blue) */}
              {allocationData.risky > 0 && (
                <circle 
                  cx="50" 
                  cy="50" 
                  r="45" 
                  fill="none" 
                  stroke="#3b82f6" 
                  strokeWidth="10"
                  strokeDasharray={`${allocationData.risky * 282.7 / 100} 282.7`}
                  strokeDashoffset="0"
                  style={{ transform: 'rotate(-90deg)', transformOrigin: '50% 50%' }}
                />
              )}
              
              {/* Safe (Green) */}
              {allocationData.safe > 0 && (
                <circle 
                  cx="50" 
                  cy="50" 
                  r="45" 
                  fill="none" 
                  stroke="#10b981" 
                  strokeWidth="10"
                  strokeDasharray={`${allocationData.safe * 282.7 / 100} 282.7`}
                  strokeDashoffset={`-${allocationData.risky * 282.7 / 100}`}
                  style={{ transform: 'rotate(-90deg)', transformOrigin: '50% 50%' }}
                />
              )}
              
              {/* Cash (Gray) */}
              {allocationData.cash > 0 && (
                <circle 
                  cx="50" 
                  cy="50" 
                  r="45" 
                  fill="none" 
                  stroke="#6b7280" 
                  strokeWidth="10"
                  strokeDasharray={`${allocationData.cash * 282.7 / 100} 282.7`}
                  strokeDashoffset={`-${(allocationData.risky + allocationData.safe) * 282.7 / 100}`}
                  style={{ transform: 'rotate(-90deg)', transformOrigin: '50% 50%' }}
                />
              )}
              
              <text x="50" y="45" textAnchor="middle" fontSize="8" fontWeight="bold" fill="#333">
                {Math.round(totalValue).toLocaleString()}
              </text>
              <text x="50" y="55" textAnchor="middle" fontSize="5" fill="#999">
                USD
              </text>
            </svg>
          </div>
          
          <div className="legend">
            <div className="legend-item">
              <span className="legend-color" style={{ backgroundColor: '#3b82f6' }}></span>
              <span className="legend-text">Risky Assets: {allocationData.risky}%</span>
            </div>
            <div className="legend-item">
              <span className="legend-color" style={{ backgroundColor: '#10b981' }}></span>
              <span className="legend-text">Safe Assets: {allocationData.safe}%</span>
            </div>
            <div className="legend-item">
              <span className="legend-color" style={{ backgroundColor: '#6b7280' }}></span>
              <span className="legend-text">Cash: {allocationData.cash}%</span>
            </div>
          </div>
        </div>

        {/* Asset Breakdown */}
        <div className="assets-section">
          <h3>Asset Breakdown</h3>
          <div className="assets-list">
            {assets.map(asset => (
              <div key={asset.symbol} className="asset-row">
                <div className="asset-info">
                  <span className="asset-color" style={{ backgroundColor: asset.color }}></span>
                  <div>
                    <div className="asset-name">{asset.name}</div>
                    <div className="asset-type">{asset.type}</div>
                  </div>
                </div>
                <div className="asset-value">
                  <span className="value">${Math.round(asset.value * 100) / 100}</span>
                  <span className="percent">{asset.value > 0 ? Math.round((asset.value / totalValue) * 100) : 0}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
