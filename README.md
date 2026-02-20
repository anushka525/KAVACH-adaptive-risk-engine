# 🛡️ Kavach Adaptive Risk Engine (KARE)

KARE is an autonomous, systematic financial decision system designed to **prioritize capital protection** using statistical market analysis and real-time portfolio rebalancing.

Unlike traditional advisory systems, KARE behaves like a **"Hedge Fund Risk Desk"**, implementing a **3-level protection cascade** that dynamically shifts between aggressive growth and complete capital preservation during market crises.

---

## 🧠 Core Philosophy

KARE operates on a **"Survival First"** mandate.

It follows a strict **Return OF Capital** strategy:
- Protect the principal before generating returns  
- Continuously monitor volatility  
- Automatically shift to safe-haven assets during high-risk conditions  

---

## 🏗️ Technical Architecture

KARE is built using a **robust full-stack architecture**:

### 🔹 Frontend
- React + Vite  
- Real-time dashboard / command center  

### 🔹 Backend
- Flask API  
- Handles data ingestion, analysis, and execution logic  

### 🔹 Database
- SQLite (via SQLAlchemy)  
- Maintains a transparent audit trail of:
  - Market states  
  - Portfolio changes  
  - Risk decisions  

---

## 🚀 Key Features

### 1️⃣ Resilient Data Pipeline (`market_data.py`)
- Ensures system reliability even during API failures  
- Implements **Primary + Fallback strategy with retries**

**Data Sources:**
- Primary → Yahoo Finance  
- Fallbacks → Stooq (Stocks/Gold), CoinGecko (Crypto)  

---

### 2️⃣ Statistical Regime Detection (`regime.py`)
Instead of black-box AI, KARE uses **quantitative finance models**.

**Approach:**
- Computes **Z-score of volatility** (30-day rolling window)

**Market Regimes:**
- 🟢 **Level 1 (Calm)**  
  `Z < 2.0` → 80% allocation to risky assets  

- 🟡 **Level 2 (Turbulent)**  
  `Z ≥ 2.0` → Shift 50% to Gold  

- 🔴 **Level 3 (Crash)**  
  `Z ≥ 3.0` → 100% liquidation into Cash  

---

### 3️⃣ Autonomous Rebalancing Engine (`rebalancer.py`)
- Executes **instant portfolio adjustments** on regime change  
- Zero-latency decision system  
- Updates allocation and persists state in database  

---

### 4️⃣ Stress Testing & Explainability

#### 🔬 Stress Testing
- Simulate artificial market crashes via `/stress-test` endpoint  
- Validate system response under extreme conditions  

#### 📜 Kavach Logs
- Every action is recorded with human-readable reasoning  
- Example:
- Volatility Z-score: 2.52 → Level 2 triggered

- Ensures full transparency and auditability  

---

## 🛠️ Tech Stack

**Languages:**
- Python 3.13+  
- JavaScript (React)  

**Frameworks:**
- Flask  
- Vite  

**Data & Analysis:**
- Pandas  

**Database:**
- SQLite (SQLAlchemy ORM)  

**Authentication:**
- Flask-Login  

---

## 📁 Project Structure

KAVACH-adaptive-risk-engine/  
│  
├── frontend/              # React frontend (UI / dashboard)  
├── app.py                 # Main Flask backend entry point  
├── models.py              # Database models (SQLAlchemy)  
├── market_data.py         # Data ingestion (Yahoo, Stooq, CoinGecko)  
├── regime.py              # Volatility + regime detection logic  
├── rebalancer.py          # Portfolio rebalancing engine  
├── requirements.txt       # Python dependencies  
├── ARCHITECTURE.txt       # System design documentation  
└── README.md              # Project documentation  

---

---

## ⚙️ Installation & Setup

### 1️⃣ Clone the repository
```bash
git clone https://github.com/anushka525/KAVACH-adaptive-risk-engine.git
cd KAVACH-adaptive-risk-engine
```
### 2️⃣ Create virtual environment
```bash
python -m venv venv
source venv/bin/activate     # Mac/Linux
venv\Scripts\activate        # Windows
```
### 3️⃣ Install dependencies
```bash
pip install -r requirements.txt
```
### 4️⃣ Run the application
- backend:
```bash
python app.py
```
- if running locally frontend:
```bash
cd frontend
npm install
npm run dev
```
Then open:
```bash
http://localhost:5173
```
