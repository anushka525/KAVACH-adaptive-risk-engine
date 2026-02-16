import './RegimeIndicator.css'

const regimeConfig = {
  bull: {
    level: 1,
    color: '#10b981',
    label: 'CALM',
    emoji: '🟢',
    description: 'Low volatility - 80% Risky Assets',
    allocation: { risky: '80%', safe: '15%', cash: '5%' }
  },
  volatile: {
    level: 2,
    color: '#f59e0b',
    label: 'TURBULENT',
    emoji: '🟠',
    description: 'High volatility - Rebalancing active',
    allocation: { risky: '40%', safe: '50%', cash: '10%' }
  },
  crash: {
    level: 3,
    color: '#ef4444',
    label: 'CRASH',
    emoji: '🔴',
    description: 'Market crisis - 100% in Cash',
    allocation: { risky: '0%', safe: '0%', cash: '100%' }
  }
}

export default function RegimeIndicator({ regime }) {
  if (!regime) return <div className="regime-loading">Loading regime...</div>

  const config = regimeConfig[regime.regime] || regimeConfig.bull
  
  return (
    <div className="regime-card card">
      <div className="regime-header">
        <span className="regime-emoji">{config.emoji}</span>
        <h3>Market Regime</h3>
      </div>
      
      <div className="regime-status" style={{ borderColor: config.color }}>
        <div className="regime-label" style={{ color: config.color }}>
          Level {config.level}: {config.label}
        </div>
        <p className="regime-description">{config.description}</p>
      </div>

      <div className="regime-details">
        <div className="detail-item">
          <span className="label">Z-Score</span>
          <span className="value">{regime.metrics?.z_score?.toFixed(2) || 'N/A'}</span>
        </div>
        <div className="detail-item">
          <span className="label">Current Vol</span>
          <span className="value">{(regime.metrics?.current_vol * 100)?.toFixed(2) || 'N/A'}%</span>
        </div>
        <div className="detail-item">
          <span className="label">Detected By</span>
          <span className="value">{regime.detected_by || 'N/A'}</span>
        </div>
      </div>

      <div className="allocation-preview">
        <h4>Target Allocation</h4>
        <div className="allocation-bars">
          <div className="allocation-item">
            <div className="bar-label">Risky</div>
            <div className="bar-container">
              <div className="bar" style={{ width: config.allocation.risky, background: '#3b82f6' }}></div>
            </div>
            <span>{config.allocation.risky}</span>
          </div>
          <div className="allocation-item">
            <div className="bar-label">Safe</div>
            <div className="bar-container">
              <div className="bar" style={{ width: config.allocation.safe, background: '#10b981' }}></div>
            </div>
            <span>{config.allocation.safe}</span>
          </div>
          <div className="allocation-item">
            <div className="bar-label">Cash</div>
            <div className="bar-container">
              <div className="bar" style={{ width: config.allocation.cash, background: '#6b7280' }}></div>
            </div>
            <span>{config.allocation.cash}</span>
          </div>
        </div>
      </div>

      {regime.rebalance && (
        <div className="alert alert-success">
          ✓ Portfolio rebalanced automatically!
        </div>
      )}
    </div>
  )
}
