// pages/Landing.tsx — Home/Landing page explaining what Smart Signal is and how it works
import { useNavigate } from 'react-router-dom'

export default function Landing() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-bg text-text-primary font-sans overflow-x-hidden">
      {/* Navbar */}
      <nav className="border-b border-border bg-panel px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded bg-[rgba(46,229,157,0.1)] border border-signal-green flex items-center justify-center">
            <div className="w-3 h-3 rounded-full bg-signal-green animate-glow-green" />
          </div>
          <span className="font-mono text-accent font-bold tracking-widest">SMART SIGNAL</span>
        </div>
        <div className="flex gap-4">
          <button onClick={() => navigate('/commuter')} className="text-sm text-text-secondary hover:text-accent transition-colors">Commuter View</button>
          <button onClick={() => navigate('/login')} className="text-sm bg-accent text-bg px-4 py-1.5 rounded font-bold hover:bg-opacity-90 transition-all">Operator Login</button>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="max-w-6xl mx-auto px-6 py-20 flex flex-col items-center text-center">
        <div className="inline-block px-3 py-1 mb-6 rounded-full border border-signal-green text-signal-green text-xs font-mono bg-[rgba(46,229,157,0.1)]">
          v1.0 Live Prototype
        </div>

        <h1 className="text-5xl md:text-7xl font-bold mb-6 tracking-tight text-white">
          The End of <span className="text-signal-red">Wasted Red Lights.</span>
        </h1>

        <p className="text-xl text-text-secondary max-w-3xl mb-12 leading-relaxed">
          Smart Signal is an AI-powered traffic control system that uses real-time computer vision
          to dynamically adapt traffic light timings based on actual vehicle density, reducing commute times,
          fuel emissions, and instantly granting priority to emergency ambulances.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 mb-20">
          <button
            onClick={() => navigate('/dashboard')}
            className="px-8 py-4 bg-accent text-bg font-bold rounded shadow-[0_0_20px_rgba(97,175,239,0.3)] hover:scale-105 transition-all text-lg"
          >
            Launch Control Room
          </button>
          <button
            onClick={() => navigate('/commuter')}
            className="px-8 py-4 bg-panel border border-border text-text-primary font-bold rounded hover:border-accent hover:text-accent transition-all text-lg"
          >
            Try Public Commuter App
          </button>
        </div>

        {/* How It Works Section */}
        <section className="mb-16">
          <h2 className="text-3xl font-bold text-center mb-8 text-white">How Smart Signal Works</h2>
          <div className="grid w-full max-w-6xl mx-auto gap-8 md:grid-cols-3">
            {/* Step 1: Detect */}
            <div className="bg-panel p-6 rounded border border-border text-center">
              <div className="text-4xl mb-4 text-signal-green">📹</div>
              <h3 className="text-xl font-bold mb-4 text-white">Detect Vehicles</h3>
              <p className="text-text-secondary">
                Uses YOLOv8 computer vision to count cars, trucks, buses and motorcycles in real-time from your webcam or uploaded video.
              </p>
            </div>

            {/* Step 2: Analyze */}
            <div className="bg-panel p-6 rounded border border-border text-center">
              <div className="text-4xl mb-4 text-signal-amber">🧠</div>
              <h3 className="text-xl font-bold mb-4 text-white">Analyze Traffic Flow</h3>
              <p className="text-text-secondary">
                Calculates traffic density and predicts clearance time for each approach using weighted vehicle counts (trucks/buses count more than cars).
              </p>
            </div>

            {/* Step 3: Adapt */}
            <div className="bg-panel p-6 rounded border border-border text-center">
              <div className="text-4xl mb-4 text-signal-red">⚡</div>
              <h3 className="text-xl font-bold mb-4 text-white">Adapt Signal Timing</h3>
              <p className="text-text-secondary">
                Dynamically adjusts traffic light phases: gives green light to busier roads, cuts short empty roads, and prevents starvation with fairness rules.
              </p>
            </div>
          </div>
        </section>

        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full text-left mb-16">
          <FeatureCard
            icon="📷"
            title="Upload or Stream Live"
            desc="The dashboard lets you upload drone footage, traffic MP4s, or connect a live webcam to test the AI vehicle detection instantly."
          />
          <FeatureCard
            icon="🧠"
            title="YOLOv8 Computer Vision"
            desc="Continuously counts vehicles and calculates traffic density to distribute green light time perfectly among lanes."
          />
          <FeatureCard
            icon="🚑"
            title="Emergency Preemption"
            desc="Detects flashing ambulance sirens and instantly overrides the intersection to give emergency vehicles a clear path."
          />
        </div>

        {/* Process Flow */}
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-bold text-center mb-6 text-white">The Adaptive Traffic Control Process</h2>
          <div className="relative h-96">
            {/* Vertical line */}
            <div className="absolute left-1/2 top-0 bottom-0 w-0.5 bg-border-soft" />

            {/* Process steps */}
            <div className="absolute left-0 top-0 w-64">
              <div className="flex items-start mb-12">
                <div className="w-10 h-10 rounded-full bg-signal-green flex items-center justify-center text-xs font-mono text-white mr-4">
                  1
                </div>
                <div className="text-sm text-text-secondary">
                  <strong>Video Input</strong><br/>
                  Webcam, uploaded video, or RTSP stream
                </div>
              </div>
              <div className="flex items-start mb-12">
                <div className="w-10 h-10 rounded-full bg-signal-green flex items-center justify-center text-xs font-mono text-white mr-4">
                  2
                </div>
                <div className="text-sm text-text-secondary">
                  <strong>AI Detection</strong><br/>
                  YOLOv8 counts vehicles in each lane
                </div>
              </div>
              <div className="flex items-start mb-12">
                <div className="w-10 h-10 rounded-full bg-signal-green flex items-center justify-center text-xs font-mono text-white mr-4">
                  3
                </div>
                <div className="text-sm text-text-secondary">
                  <strong>Traffic Analysis</strong><br/>
                  Calculates density and predicts clearance time
                </div>
              </div>
              <div className="flex items-start mb-12">
                <div className="w-10 h-10 rounded-full bg-signal-green flex items-center justify-center text-xs font-mono text-white mr-4">
                  4
                </div>
                <div className="text-sm text-text-secondary">
                  <strong>Signal Control</strong><br/>
                  AI decides optimal light phases and timing
                </div>
              </div>
              <div className="flex items-start">
                <div className="w-10 h-10 rounded-full bg-signal-green flex items-center justify-center text-xs font-mono text-white mr-4">
                  5
                </div>
                <div className="text-sm text-text-secondary">
                  <strong>Output</strong><br/>
                  Adaptive traffic light timing with emergency preemption
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-border mt-20 py-8 text-center text-text-muted text-sm font-mono">
        Built for the Entrepreneurship & Design Thinking Track.
      </footer>
    </div>
  )
}

function FeatureCard({ icon, title, desc }: { icon: string, title: string, desc: string }) {
  return (
    <div className="bg-panel border border-border p-6 rounded hover:border-accent transition-colors">
      <div className="text-3xl mb-4">{icon}</div>
      <h3 className="text-lg font-bold text-white mb-2">{title}</h3>
      <p className="text-text-secondary text-sm leading-relaxed">{desc}</p>
    </div>
  )
}