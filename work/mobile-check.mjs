import { chromium } from 'playwright'

const baseUrl = process.env.PUBLIC_BASE_URL || 'https://txwapis.com'
const password = process.env.APP_PASSWORD
if (!password) {
  throw new Error('APP_PASSWORD is required')
}

const loginRes = await fetch(`${baseUrl}/api/v1/auth/login`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ password }),
})

if (!loginRes.ok) {
  throw new Error(`Login failed: ${loginRes.status} ${await loginRes.text()}`)
}

const { token } = await loginRes.json()
const browser = await chromium.launch({ channel: 'chrome' })
const page = await browser.newPage({ viewport: { width: 390, height: 844 } })

await page.addInitScript((jwt) => {
  window.localStorage.setItem('token', jwt)
}, token)

await page.goto(`${baseUrl}/invoices/upload`, { waitUntil: 'networkidle' })
await page.screenshot({
  path: 'C:/Users/PC/Documents/Codex/2026-06-29/txwapis/outputs/upload-mobile-after.png',
  fullPage: true,
})

console.log(await page.locator('body').innerText({ timeout: 3000 }))
await browser.close()
