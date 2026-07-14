import React, { useState } from 'react'
import ReactDOM from 'react-dom/client'
import CircleOfMorality from './CircleOfMorality'
import ScreenplayTracker from './ScreenplayTracker'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
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
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
)
