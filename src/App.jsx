import { Routes, Route, Link, useLocation } from 'react-router-dom'
import CircleOfMorality from './CircleOfMorality'
import ProductionDashboard from './components/production/ProductionDashboard'
import EpisodeManager from './components/production/EpisodeManager'
import PipelineMonitor from './components/production/PipelineMonitor'
import ScriptEditor from './components/production/ScriptEditor'
import AssetGallery from './components/production/AssetGallery'
import VideoPreview from './components/production/VideoPreview'
import UploadPanel from './components/production/UploadPanel'
import WarRoom from './components/production/WarRoom'
import ControlRoom from './components/production/ControlRoom'
import DiscoveryFeed from './components/production/DiscoveryFeed'

function Nav() {
  const loc = useLocation()
  const isCircle = loc.pathname === '/circle'
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between
                    px-6 h-12 bg-black/80 backdrop-blur border-b border-amber-900/20">
      <Link to="/" className="font-display text-amber-600 text-xl tracking-widest border-none hover:text-amber-400">
        BGF
      </Link>
      <div className="flex items-center gap-6 text-xs font-mono tracking-widest uppercase">
        <Link to="/" className={`border-none transition-colors ${!isCircle ? 'text-amber-400' : 'text-stone-600 hover:text-stone-400'}`}>
          Production
        </Link>
        <Link to="/discover" className="text-stone-600 hover:text-amber-600 border-none transition-colors">
          Discover
        </Link>
        <Link to="/war-room" className="text-stone-600 hover:text-amber-600 border-none transition-colors">
          War Room
        </Link>
        <Link to="/circle" className="text-stone-600 hover:text-stone-400 border-none transition-colors">
          Circle
        </Link>
        <Link to="/control-room" className="text-stone-600 hover:text-violet-400 border-none transition-colors">
          Control Room
        </Link>
      </div>
    </nav>
  )
}

export default function App() {
  return (
    <div className="min-h-screen bg-stone-950 text-amber-50 pt-12">
      <Nav />
      <Routes>
        <Route path="/" element={<ProductionDashboard />} />
        <Route path="/new" element={<EpisodeManager />} />
        <Route path="/discover" element={<DiscoveryFeed />} />
        <Route path="/war-room" element={<WarRoom />} />
        <Route path="/circle" element={<CircleOfMorality />} />
        <Route path="/episodes/:id/pipeline" element={<PipelineMonitor />} />
        <Route path="/episodes/:id/script" element={<ScriptEditor />} />
        <Route path="/episodes/:id/assets" element={<AssetGallery />} />
        <Route path="/episodes/:id/preview" element={<VideoPreview />} />
        <Route path="/episodes/:id/upload" element={<UploadPanel />} />
        <Route path="/episodes/:id/control-room" element={<ControlRoom />} />
        <Route path="/episodes/:id" element={<PipelineMonitor />} />
        <Route path="/control-room" element={<div className="max-w-xl mx-auto px-4 py-16 text-center text-stone-600 font-ui text-sm">
          Open an episode to view its Control Room.
        </div>} />
      </Routes>
    </div>
  )
}
