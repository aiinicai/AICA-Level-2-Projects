import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { FinancialsProvider } from './context/FinancialsContext.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <FinancialsProvider>
      <App />
    </FinancialsProvider>
  </StrictMode>,
)
