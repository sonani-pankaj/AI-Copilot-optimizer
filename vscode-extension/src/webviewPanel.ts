// See: specs/vscode-extension/webview-panel.md
import * as vscode from 'vscode'

interface PanelState {
  loading?: boolean
  response?: string
  cacheHit?: boolean
  similarity?: number | null
  promptType?: string
  error?: string
}

export class AiPromptPanel {
  private static instance: AiPromptPanel | undefined
  private readonly panel: vscode.WebviewPanel

  private constructor(context: vscode.ExtensionContext) {
    this.panel = vscode.window.createWebviewPanel(
      'aiCopilotOptimizer',
      'AI Copilot Optimizer',
      vscode.ViewColumn.Beside,
      { enableScripts: true, retainContextWhenHidden: true }
    )

    this.panel.webview.onDidReceiveMessage(async (msg) => {
      if (msg.type === 'copy') {
        await vscode.env.clipboard.writeText(msg.text)
        vscode.window.showInformationMessage('Copied to clipboard')
      }
    })

    this.panel.onDidDispose(() => {
      AiPromptPanel.instance = undefined
    })

    this.setState({ loading: true })
  }

  static getOrCreate(context: vscode.ExtensionContext): AiPromptPanel {
    if (!AiPromptPanel.instance) {
      AiPromptPanel.instance = new AiPromptPanel(context)
    } else {
      AiPromptPanel.instance.panel.reveal(vscode.ViewColumn.Beside, true)
    }
    return AiPromptPanel.instance
  }

  setState(state: PanelState): void {
    this.panel.webview.html = this.renderHtml(state)
  }

  private renderHtml(state: PanelState): string {
    const { loading, response, cacheHit, similarity, promptType, error } = state
    const escaped = response
      ? response.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      : ''

    return /* html */ `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>AI Copilot Optimizer</title>
  <style>
    body { font-family: var(--vscode-font-family); color: var(--vscode-foreground);
           background: var(--vscode-editor-background); padding: 20px; }
    h2 { margin-top: 0; color: #7c6af7; }
    .badge { display: inline-block; padding: 2px 10px; border-radius: 20px;
             font-size: 11px; font-weight: 700; margin-right: 8px; }
    .cache-hit  { background: #14532d; color: #4ade80; }
    .cache-miss { background: #1c1917; color: #fb923c; }
    pre { white-space: pre-wrap; word-break: break-word; background: #1a1d27;
          border-radius: 8px; padding: 16px; font-size: 13px; }
    button { background: #7c6af7; color: #fff; border: none; padding: 8px 18px;
             border-radius: 6px; cursor: pointer; margin-right: 8px; }
    .spinner { display: inline-block; width: 24px; height: 24px; border: 3px solid #2d3148;
               border-top-color: #7c6af7; border-radius: 50%; animation: spin 0.7s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }
    .error { color: #f87171; background: #450a0a; padding: 12px; border-radius: 8px; }
  </style>
</head>
<body>
  <h2>⚡ AI Copilot Optimizer</h2>

  ${loading ? '<div class="spinner"></div><p>Querying backend…</p>' : ''}

  ${error ? `<div class="error">⚠ ${error}</div>` : ''}

  ${response ? `
  <div style="margin-bottom:12px">
    <span class="badge ${cacheHit ? 'cache-hit' : 'cache-miss'}">
      ${cacheHit ? '✓ Cache Hit' : '○ LLM'}
    </span>
    ${similarity != null ? `<span style="color:#94a3b8;font-size:12px">similarity: ${(similarity * 100).toFixed(1)}%</span>` : ''}
    ${promptType ? `<span style="color:#94a3b8;font-size:12px;margin-left:8px">${promptType}</span>` : ''}
  </div>
  <pre id="responseBlock">${escaped}</pre>
  <button onclick="copyResponse()">Copy</button>
  ` : ''}

  <script>
    const vscode = acquireVsCodeApi();
    function copyResponse() {
      vscode.postMessage({ type: 'copy', text: document.getElementById('responseBlock').innerText });
    }
  </script>
</body>
</html>`
  }
}
