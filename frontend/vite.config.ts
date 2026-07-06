import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      injectRegister: 'auto',
      includeAssets: ['favicon.ico', 'apple-touch-icon.png', 'masked-icon.svg'],
      manifest: {
        name: 'SafeKid Monitor',
        short_name: 'SafeKid',
        description: 'Hệ thống giám sát an toàn trẻ em qua camera edge',
        theme_color: '#0058be', // Navy primary color of the system
        background_color: '#ffffff',
        display: 'standalone',
        orientation: 'portrait',
        start_url: './',
        scope: './',
        icons: [
          {
            src: 'icons/icon-192.png',
            sizes: '192x192',
            type: 'image/png'
          },
          {
            src: 'icons/icon-512.png',
            sizes: '512x512',
            type: 'image/png'
          },
          {
            src: 'icons/maskable-icon-512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable'
          }
        ]
      },
      workbox: {
        // Exclude sensitive routes from service worker cache
        // Không cache video, snapshot cảnh báo hoặc API bảo mật vì đây là dữ liệu liên quan đến trẻ em.
        navigateFallbackDenylist: [
          /^\/api/,
          /^\/snapshots/,
          /^\/ws/,
          /^\/ws\/signaling/
        ],
        runtimeCaching: [
          {
            // API calls and secure WebRTC signaling must never be cached
            urlPattern: /^\/(api|snapshots|ws|ws\/signaling)/,
            handler: 'NetworkOnly'
          },
          {
            // Cache static assets like JS, CSS, index.html, static images
            urlPattern: /\.(?:js|css|html|png|jpg|jpeg|svg|ico)$/,
            handler: 'StaleWhileRevalidate',
            options: {
              cacheName: 'static-resources',
              expiration: {
                maxEntries: 50,
                maxAgeSeconds: 30 * 24 * 60 * 60 // 30 days
              }
            }
          },
          {
            // Cache fonts from Google APIs
            urlPattern: /^https:\/\/fonts\.(?:googleapis|gstatic)\.com/,
            handler: 'CacheFirst',
            options: {
              cacheName: 'google-fonts',
              expiration: {
                maxEntries: 10,
                maxAgeSeconds: 365 * 24 * 60 * 60 // 1 year
              }
            }
          }
        ]
      }
    })
  ]
})
