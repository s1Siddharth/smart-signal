// pages/Settings.tsx — Settings and controls
import { useRef, useState } from 'react'
import { api } from '@/lib/api'

export default function Settings() {
  const [source, setSource] = useState('0')
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [demoSpeed, setDemoSpeed] = useState(1) // 1 = real-time
  const [currentSourceLabel, setCurrentSourceLabel] = useState('Webcam')
  const [isPlaying, setIsPlaying] = useState(true) // Video playback state

  const handleSimulate = async (road: string) => {
    await api.simulateAmbulance(road)
  }

  const handleSourceChange = async (override?: string) => {
    await api.switchSource(override ?? source)
    // Update label based on source
    if (override === '0' || source === '0') {
      setCurrentSourceLabel('Webcam')
      setIsPlaying(true) // Reset to playing state for webcam
    } else if (override && override.startsWith('samples/')) {
      setCurrentSourceLabel(`Video: ${override.split('/').pop()}`)
      // For uploaded videos, we might want to start paused or add a preview
    } else {
      setCurrentSourceLabel(override || source)
    }
  }

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      await api.uploadVideo(file)
      setSource(`samples/${file.name}`)
      setCurrentSourceLabel(`Video: ${file.name}`)
      // When a new video is uploaded, start with it paused so user can choose to play
      setIsPlaying(false)
    } catch (err) {
      alert('Failed to upload video')
    } finally {
      setUploading(false)
    }
  }

  const handleDemoSpeedChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const speed = parseFloat(e.target.value)
    setDemoSpeed(speed)
    try {
      await api.updateConfig({ DEMO_SPEED: speed })
    } catch (err) {
      alert('Failed to update demo speed')
      // Reset to previous value on error
      setDemoSpeed(1)
    }
  }

  // Handle manual source change
  const handleManualSourceChange = () => {
    handleSourceChange()
  }

  // Toggle video play/pause
  const toggleVideoPlay = async () => {
    setIsPlaying(!isPlaying)
    // Send playback state to backend if needed
    try {
      await api.updateConfig({
        VIDEO_PLAYBACK: isPlaying ? 'pause' : 'play'
      })
    } catch (err) {
      // If backend doesn't support it yet, we'll handle it frontend-only
      console.log('Backend playback control not implemented yet')
    }
  }

  // Clear/video reset - go back to webcam
  const clearVideo = () => {
    handleSourceChange('0')
  }

  return (
    <div className="p-6 text-text-primary">
      <h1 className="text-xl font-bold mb-4 font-sans text-accent">Control Room Settings</h1>

      <div className="bg-panel p-4 rounded border border-border mb-4">
        <h2 className="text-sm font-semibold mb-3 font-sans uppercase tracking-wider">Simulate Ambulance</h2>
        <div className="flex gap-2">
          {['A', 'B', 'C', 'D'].map(r => (
            <button
              key={r}
              onClick={() => handleSimulate(r)}
              className="bg-[rgba(255,176,32,0.1)] border border-signal-amber text-signal-amber px-4 py-2 rounded text-sm font-bold hover:bg-signal-amber hover:text-bg transition-colors font-sans"
            >
              Force Road {r}
            </button>
          ))}
        </div>
        <p className="mt-2 text-text-muted text-xs font-mono">Triggers emergency priority (turns target road green, forces others red)</p>
      </div>

      <div className="bg-panel p-4 rounded border border-border mb-4">
        <h2 className="text-sm font-semibold mb-3 font-sans uppercase tracking-wider">Video Source Engine</h2>

        <div className="flex flex-col gap-4">
          {/* Current source indicator with controls */}
          <div className="flex items-center gap-3 mb-4 p-3 bg-border rounded">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full
                  {currentSourceLabel.startsWith('Video') ? 'bg-signal-amber' : 'bg-signal-green'}">
              </div>
              <span className="font-mono text-sm">{currentSourceLabel}</span>
            </div>

            {/* Play/Pause controls for video (only show when video source) */}
            {currentSourceLabel.startsWith('Video') && (
              <div className="flex items-center gap-2">
                <button
                  onClick={toggleVideoPlay}
                  className="p-2 rounded hover:bg-accent hover:text-bg transition-colors font-sans text-xs"
                  title={isPlaying ? 'Pause Video' : 'Play Video'}
                >
                  {isPlaying ? '⏸' : '▶️'}
                </button>
                <button
                  onClick={clearVideo}
                  className="text-xs font-sans text-signal-red hover:text-signal-red/80"
                  title="Clear Video"
                >
                  ✕
                </button>
              </div>
            )}
          </div>

          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-3">
              <button
                onClick={() => handleSourceChange('0')}
                className="w-full justify-start bg-[rgba(46,229,157,0.1)] border border-signal-green text-signal-green px-4 py-2 rounded text-sm font-bold hover:bg-signal-green hover:text-bg transition-colors"
              >
                Use Live Webcam
              </button>
              <span className="text-text-muted text-xs font-mono">Connect to local camera index 0</span>
            </div>

            <div className="flex items-center gap-3">
              <input
                type="file"
                accept="video/mp4,video/x-m4v,video/*"
                className="hidden"
                ref={fileInputRef}
                onChange={handleFileChange}
              />
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                className="w-full justify-start bg-[rgba(97,175,239,0.1)] border border-accent text-accent px-4 py-2 rounded text-sm font-bold hover:bg-accent hover:text-bg transition-colors disabled:opacity-50 font-sans"
              >
                {uploading ? 'Uploading...' : 'Upload Video File'}
              </button>
              <span className="text-text-muted text-xs font-mono">Upload an .mp4 file to stream continuously</span>
            </div>

            <div className="flex items-center gap-3">
              <div className="flex w-full space-x-3">
                <input
                  type="text"
                  value={source}
                  onChange={e => setSource(e.target.value)}
                  className="flex-1 bg-bg border border-border rounded px-3 py-1.5 flex-grow font-mono text-sm focus:border-accent outline-none transition-colors"
                  placeholder="0 for webcam, or path/to/video.mp4"
                />
                <button
                  onClick={handleManualSourceChange}
                  className="bg-panel border border-border text-text-primary hover:border-accent hover:text-accent px-4 py-1.5 rounded text-sm font-bold transition-colors font-sans"
                >
                  Apply Custom Source
                </button>
              </div>
              <span className="text-text-muted text-xs font-mono block">Or manual input (RTSP stream or exact path):</span>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-panel p-4 rounded border border-border">
        <h2 className="text-sm font-semibold mb-3 font-sans uppercase tracking-wider">Demo Settings</h2>

        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2">
              Demo Speed Multiplier:
              <span className="text-text-secondary">{demoSpeed}×</span>
            </label>
            <input
              type="range"
              min="0.1"
              max="20"
              step="0.1"
              value={demoSpeed}
              onChange={handleDemoSpeedChange}
              className="w-full"
            />
          </div>
          <div className="text-text-muted text-xs font-mono">
            In demo mode: 120s cycle becomes {Math.round(120 / demoSpeed)}s at {demoSpeed}× speed
          </div>
          <div className="text-text-muted text-xs font-mono">
            Higher speeds make demos faster but reduce real-time accuracy
          </div>
        </div>
      </div>
    </div>
  )
}