import './App.css'

function App() {
  return (
    <div className="app">
      <header className="header">
        <div className="logo">MARK</div>
        <a href="#" className="login-link">Login</a>
      </header>

      <main className="main">
        <section className="hero">
          <h1>
            ATTENDANCE
            <span className="accent">MADE SIMPLE</span>
          </h1>
          <p>Record a 10-second classroom video. Our AI identifies every student and marks attendance automatically. No more roll calls.</p>
        </section>

        <section className="features">
          <div className="feature-card">
            <div className="feature-number">01</div>
            <h3 className="feature-title">Quick Capture</h3>
            <p className="feature-desc">Record a brief 10-second video of your classroom using any device.</p>
          </div>
          <div className="feature-card">
            <div className="feature-number">02</div>
            <h3 className="feature-title">AI Detection</h3>
            <p className="feature-desc">Advanced facial recognition instantly identifies each enrolled student.</p>
          </div>
          <div className="feature-card">
            <div className="feature-number">03</div>
            <h3 className="feature-title">Auto Marking</h3>
            <p className="feature-desc">Attendance records generated and synced to your dashboard in seconds.</p>
          </div>
        </section>

      </main>

      <footer className="footer">
        <p>&copy; 2026 MARK</p>
        <div className="footer-links">
          <a href="#">Privacy</a>
          <a href="#">Terms</a>
          <a href="#">Contact</a>
        </div>
      </footer>
    </div>
  )
}

export default App
