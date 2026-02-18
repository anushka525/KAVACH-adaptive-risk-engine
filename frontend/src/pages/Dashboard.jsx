import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { toastService } from '../utils/toastService'
import RegimeIndicator from '../components/RegimeIndicator'
import './Dashboard.css'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:5000'

const ALLOCATION_RULES = {
  bull: { risky: 80, safe: 15, cash: 5 },
  volatile: { risky: 40, safe: 50, cash: 10 },
  crash: { risky: 0, safe: 0, cash: 100 }
}

export default function Dashboard({ onLogout }) {
  const [user, setUser] = useState(null)
  const [regime, setRegime] = useState(null)
  const [lastRebalance, setLastRebalance] = useState(null)
  const [deployed, setDeployed] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [deploying, setDeploying] = useState(false)
  const [testingStress, setTestingStress] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    fetchUserData()
  }, [])

  const fetchUserData = async () => {
    try {
      const response = await fetch(`${API_BASE}/me`, {
        credentials: 'include'
      })
      if (!response.ok) throw new Error('Unauthorized')
      
      const userData = await response.json()
      setUser(userData)
      setDeployed(userData.deployed)
      if (userData.deployed) {
        fetchRegime()
      }
    } catch (err) {
      if (err.message === 'Unauthorized') {
        handleLogout()
      } else {
        setError('Failed to load user data')
      }
    } finally {
      setLoading(false)
    }
  }

  const fetchRegime = async () => {
    try {
      toastService.info('📊 Checking market regime...')
      const response = await fetch(`${API_BASE}/regime`, {
        credentials: 'include'
      })
      const regimeData = await response.json()
      if (regimeData.rebalance) {
        setLastRebalance(regimeData.rebalance)
        toastService.success('✅ Portfolio rebalanced! Regime changed to Level ' + regimeData.level)
      } else {
        setLastRebalance(null)
      }
      setRegime(regimeData)
      toastService.info(`📈 Market: Level ${regimeData.level} (${regimeData.regime})`)
    } catch (err) {
      setError('Failed to fetch regime data')
      toastService.error('Failed to fetch regime data')
    }
  }

  const handleDeploy = async () => {
    setDeploying(true)
    const toastId = toastService.loading('🚀 Deploying capital...')
    setError('')
    try {
      const response = await fetch(`${API_BASE}/deploy`, {
        method: 'POST',
        credentials: 'include'
      })
      const result = await response.json()
      
      if (result.message === 'Capital deployed successfully') {
        setDeployed(true)
        await fetchUserData()
        await fetchRegime()
        toastService.update(toastId, {
          render: `✅ Capital deployed successfully!\nAllocated: ${result.regime} regime`,
          type: 'success',
          isLoading: false,
          autoClose: 3000
        })
      } else {
        setError(result.error || 'Deployment failed')
        toastService.update(toastId, {
          render: `❌ ${result.error || 'Deployment failed'}`,
          type: 'error',
          isLoading: false,
          autoClose: 4000
        })
      }
    } catch (err) {
      setError('Failed to deploy capital')
      toastService.update(toastId, {
        render: '❌ Failed to connect to server',
        type: 'error',
        isLoading: false,
        autoClose: 4000
      })
    } finally {
      setDeploying(false)
    }
  }

  const handleStressTest = async () => {
    setTestingStress(true)
    const toastId = toastService.loading('⚡ Running stress test (simulating crash)...')
    setError('')
    try {
      const response = await fetch(`${API_BASE}/stress-test`, {
        method: 'POST',
        credentials: 'include'
      })
      const result = await response.json()
      
      if (result.status === 'stress test executed') {
        if (result.rebalance_details) {
          setLastRebalance(result.rebalance_details)
        }
        await fetchRegime()
        toastService.update(toastId, {
          render: '✅ Stress test complete!\n🛡️ Portfolio moved to 100% cash (Level 3)',
          type: 'success',
          isLoading: false,
          autoClose: 5000
        })
      } else {
        setError(result.error || 'Stress test failed')
        toastService.update(toastId, {
          render: `❌ ${result.error || 'Stress test failed'}`,
          type: 'error',
          isLoading: false,
          autoClose: 4000
        })
      }
    } catch (err) {
      setError('Failed to run stress test')
      toastService.update(toastId, {
        render: '❌ Failed to run stress test',
        type: 'error',
        isLoading: false,
        autoClose: 4000
      })
    } finally {
      setTestingStress(false)
    }
  }

  const handleLogout = async () => {
    try {
      await fetch(`${API_BASE}/logout`, {
        method: 'POST',
        credentials: 'include'
      })
    } catch (err) {
      // Continue logout even if request fails
    }
    localStorage.removeItem('email')
    localStorage.removeItem('authToken')
    onLogout()
    navigate('/login')
  }

  const getAllocationSummary = () => {
    if (!deployed) {
      return { risky: 0, safe: 0, cash: 0, source: 'Deploy to see allocation' }
    }

    if (lastRebalance?.allocation) {
      const allocation = lastRebalance.allocation
      const total =
        lastRebalance.portfolio_value ||
        Object.values(allocation).reduce((sum, value) => sum + value, 0) ||
        1

      const riskyValue = (allocation['BTC-USD'] || 0) + (allocation['ETH-USD'] || 0)
      const safeValue = allocation['GLD'] || 0
      const cashValue = allocation['USD'] || 0

      return {
        risky: Math.round((riskyValue / total) * 100),
        safe: Math.round((safeValue / total) * 100),
        cash: Math.round((cashValue / total) * 100),
        source: 'Latest rebalance'
      }
    }

    const target = ALLOCATION_RULES[regime?.regime] || ALLOCATION_RULES.bull
    return {
      ...target,
      source: 'Target allocation'
    }
  }

  const allocationSummary = getAllocationSummary()

  if (loading) {
    return (
      <div className="dashboard-loading">
        <div className="spinner"></div>
      </div>
    )
  }

  return (
    <div className="dashboard">
      {/* Header */}
      <header className="dashboard-header">
        <div className="header-left">
          <h1>🛡️ KARE Dashboard</h1>
          <p>Adaptive Portfolio Protection</p>
        </div>
        <div className="header-right">
          <div className="user-info">
            <span className="username">{user?.username}</span>
            <button className="btn-secondary" onClick={handleLogout}>
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="container dashboard-content">
        {error && <div className="alert alert-error">{error}</div>}

        {/* Status Section */}
        <div className="status-section">
          {deployed ? (
            <>
              <RegimeIndicator regime={regime} />
              <div className="portfolio-summary card">
                <h3>Portfolio Status</h3>
                <p className="status-label">Active & Protected</p>
                <p className="status-value">✓</p>
              </div>
              <div className="allocation-summary card">
                <h3>Rebalance Summary</h3>
                {!regime ? (
                  <div className="loading-state">
                    <div className="spinner-small"></div>
                    <p>Loading regime data...</p>
                  </div>
                ) : (
                  <>
                    <p className="summary-source">{allocationSummary.source}</p>
                    <div className="summary-row">
                      <span>Risky</span>
                      <span>{allocationSummary.risky}%</span>
                    </div>
                    <div className="summary-row">
                      <span>Safe</span>
                      <span>{allocationSummary.safe}%</span>
                    </div>
                    <div className="summary-row">
                      <span>Cash</span>
                      <span>{allocationSummary.cash}%</span>
                    </div>
                  </>
                )}
              </div>
            </>
          ) : (
            <div className="not-deployed card">
              <h2>Ready to Deploy?</h2>
              <p>Deploy your $100k dummy capital to start portfolio protection</p>
              <button 
                className="btn-primary" 
                onClick={handleDeploy}
                disabled={deploying}
              >
                {deploying ? <>Deploying...</> : '🚀 Deploy Capital'}
              </button>
            </div>
          )}
        </div>

        {/* Actions */}
        {deployed && (
          <>
            {/* Action Buttons */}
            <div className="actions-section">
              <h3>Test & Monitor</h3>
              <div className="actions-grid">
                <button 
                  className="btn-warning"
                  onClick={fetchRegime}
                >
                  📊 Check Regime
                </button>
                <button 
                  className="btn-danger"
                  onClick={handleStressTest}
                  disabled={testingStress}
                >
                  {testingStress ? <>Testing...</> : '⚡ Run Stress Test'}
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
