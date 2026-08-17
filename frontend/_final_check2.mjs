import { chromium } from 'playwright'

const FINGERPRINT_PATH = '/private/tmp/claude-501/-Users-swetarai-AI-Brainnetwork/848d5b14-0547-4d75-8300-c6c8fa845d44/scratchpad/test_fingerprint.png'
const errors = []
const browser = await chromium.launch({ args: ['--no-sandbox'] })
const page = await browser.newPage({ viewport: { width: 390, height: 844 } }) // iPhone-ish viewport
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()) })
page.on('pageerror', (e) => errors.push(e.message))

// manifest reachable
const manifestResp = await page.goto('http://localhost:5173/manifest.json')
console.log('manifest status:', manifestResp.status())
console.log('manifest body:', (await manifestResp.text()).slice(0, 200))

await page.goto('http://localhost:5173/profile/enroll', { waitUntil: 'networkidle' })
await page.locator('input[type=file]').setInputFiles(FINGERPRINT_PATH)
await page.waitForSelector('text=Image quality', { timeout: 15000 })
await page.check('input[type=checkbox]')
await page.click('button:has-text("Build Individual Computational Profile")')
await page.waitForSelector('h2:has-text("Your Individual Computational Profile")', { timeout: 20000 })
console.log('enroll OK, waiting for auto-advance...')

await page.waitForURL('**/profile', { timeout: 5000 })
console.log('auto-advanced to Overview:', page.url())

await page.fill('#overview-query', 'Write a short poem about the ocean.')
await page.click('button:has-text("Ask")')
await page.waitForSelector('text=Activated Virtual Systems', { timeout: 20000 })
const category = await page.locator('text=Task classified as').innerText()
console.log('classification:', category)

await page.screenshot({ path: '/private/tmp/claude-501/-Users-swetarai-AI-Brainnetwork/848d5b14-0547-4d75-8300-c6c8fa845d44/scratchpad/screenshots/16-mobile-viewport-final.png', fullPage: true })

console.log('console/page errors:', errors.length ? errors.join('\n') : '(none)')
await browser.close()
