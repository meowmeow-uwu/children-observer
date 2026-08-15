import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// Phòng vệ bổ sung cho localhost dev sau khi từng chạy Docker/PWA trên cùng
// origin: dọn registration và cache cũ. Production không đi qua nhánh này.
if (import.meta.env.DEV) {
  window.addEventListener('load', () => {
    navigator.serviceWorker?.getRegistrations().then((registrations) => {
      registrations.forEach((registration) => registration.unregister())
    })
    window.caches?.keys().then((names) => {
      names.forEach((name) => window.caches.delete(name))
    })
  }, { once: true })
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
