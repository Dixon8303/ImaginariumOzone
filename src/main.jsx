import React, { useState } from 'react'
import ReactDOM from 'react-dom/client'
import CircleOfMorality from './CircleOfMorality'
import ScreenplayTracker from './ScreenplayTracker'
import './index.css'

function App() {
  const [view, setView] = useState('morality')

  return view === 'morality'
    ? <CircleOfMorality onOpenTracker={() => setView('tracker')} />
    : <ScreenplayTracker onClose={() => setView('morality')} />
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
