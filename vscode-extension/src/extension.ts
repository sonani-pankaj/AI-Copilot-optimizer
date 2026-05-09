// See: specs/vscode-extension/build-prompt-command.md
import * as vscode from 'vscode'
import { buildPrompt, buildPromptFromFolder } from './promptBuilder'
import { queryBackend } from './backendClient'
import { AiPromptPanel } from './webviewPanel'

export function activate(context: vscode.ExtensionContext): void {

  // Command: build prompt for a folder (right-click in Explorer)
  const buildFolderCmd = vscode.commands.registerCommand(
    'ai-copilot-optimizer.buildPromptFolder',
    (folderUri?: vscode.Uri) => runBuildPromptFromFolder(context, folderUri)
  )

  // Command: manually trigger from command palette
  const buildCmd = vscode.commands.registerCommand(
    'ai-copilot-optimizer.buildPrompt',
    () => runBuildPrompt(context)
  )

  // Command: set JWT token in SecretStorage
  const setTokenCmd = vscode.commands.registerCommand(
    'ai-copilot-optimizer.setToken',
    async () => {
      const token = await vscode.window.showInputBox({
        prompt: 'Enter your JWT token from the dashboard',
        password: true,
        ignoreFocusOut: true,
      })
      if (token) {
        await context.secrets.store('ai-copilot-optimizer.jwt', token)
        vscode.window.showInformationMessage('AI Copilot Optimizer: Token saved.')
      }
    }
  )

  // Auto-run on save for Java files
  const onSave = vscode.workspace.onDidSaveTextDocument((doc) => {
    if (doc.languageId === 'java') {
      runBuildPrompt(context)
    }
  })

  context.subscriptions.push(buildCmd, buildFolderCmd, setTokenCmd, onSave)
}

async function runBuildPrompt(context: vscode.ExtensionContext): Promise<void> {
  const editor = vscode.window.activeTextEditor
  if (!editor || editor.document.languageId !== 'java') {
    return // silently skip non-Java files
  }

  const jwt = await context.secrets.get('ai-copilot-optimizer.jwt')
  if (!jwt) {
    vscode.window.showErrorMessage(
      'AI Copilot Optimizer: No token found. Run "Set Backend JWT Token" first.'
    )
    return
  }

  // Show panel immediately with loading state
  const panel = AiPromptPanel.getOrCreate(context)
  panel.setState({ loading: true })

  try {
    const payload = await buildPrompt(editor)
    const result = await queryBackend(payload, jwt, context)
    panel.setState({
      loading: false,
      response: result.response,
      cacheHit: result.cache_hit,
      similarity: result.similarity,
      promptType: payload.prompt_type,
    })
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err)
    panel.setState({ loading: false, error: msg })
  }
}

async function runBuildPromptFromFolder(
  context: vscode.ExtensionContext,
  folderUri?: vscode.Uri
): Promise<void> {
  const uri = folderUri ?? vscode.workspace.workspaceFolders?.[0]?.uri
  if (!uri) {
    vscode.window.showErrorMessage('AI Copilot Optimizer: No folder selected.')
    return
  }

  const jwt = await context.secrets.get('ai-copilot-optimizer.jwt')
  if (!jwt) {
    vscode.window.showErrorMessage(
      'AI Copilot Optimizer: No token found. Run "Set Backend JWT Token" first.'
    )
    return
  }

  const panel = AiPromptPanel.getOrCreate(context)
  panel.setState({ loading: true })

  try {
    const payload = await buildPromptFromFolder(uri)
    const result = await queryBackend(payload, jwt, context)
    panel.setState({
      loading: false,
      response: result.response,
      cacheHit: result.cache_hit,
      similarity: result.similarity,
      promptType: payload.prompt_type,
    })
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err)
    panel.setState({ loading: false, error: msg })
  }
}

export function deactivate(): void {}
