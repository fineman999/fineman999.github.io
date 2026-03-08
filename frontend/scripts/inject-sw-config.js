import { readFileSync, writeFileSync } from 'fs'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const swPath = resolve(__dirname, '../dist/sw.js')
let content = readFileSync(swPath, 'utf-8')
content = content.replace('__FIREBASE_CONFIG__', process.env.VITE_FIREBASE_CONFIG || '{}')
writeFileSync(swPath, content)
console.log('sw.js: Firebase config injected')
