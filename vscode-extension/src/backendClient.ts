// See: specs/vscode-extension/build-prompt-command.md
import * as vscode from 'vscode'
import * as https from 'https'
import * as http from 'http'
import { PromptPayload } from './promptBuilder'

export interface QueryResult {
  response: string
  cache_hit: boolean
  similarity: number | null
  tokens_used: number
}

export async function queryBackend(
  payload: PromptPayload,
  jwt: string,
  context: vscode.ExtensionContext
): Promise<QueryResult> {
  const backendUrl = vscode.workspace
    .getConfiguration('ai-copilot-optimizer')
    .get<string>('backendUrl', 'http://localhost:8000')

  const url = new URL('/query', backendUrl)
  const body = JSON.stringify(payload)

  return new Promise((resolve, reject) => {
    const mod = url.protocol === 'https:' ? https : http
    const req = mod.request(
      {
        hostname: url.hostname,
        port: url.port || (url.protocol === 'https:' ? 443 : 80),
        path: url.pathname,
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(body),
          Authorization: `Bearer ${jwt}`,
        },
      },
      (res) => {
        const chunks: Buffer[] = []
        res.on('data', (c: Buffer) => chunks.push(c))
        res.on('end', () => {
          const raw = Buffer.concat(chunks).toString()
          if (res.statusCode === 401) {
            // Clear stale token
            context.secrets.delete('ai-copilot-optimizer.jwt')
            reject(new Error('Unauthorized — please re-run "Set Backend JWT Token"'))
            return
          }
          if (!res.statusCode || res.statusCode >= 400) {
            reject(new Error(`Backend error ${res.statusCode}: ${raw}`))
            return
          }
          try {
            resolve(JSON.parse(raw) as QueryResult)
          } catch {
            reject(new Error('Invalid JSON from backend'))
          }
        })
      }
    )
    req.on('error', reject)
    req.write(body)
    req.end()
  })
}
