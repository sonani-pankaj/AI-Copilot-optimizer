// See: specs/vscode-extension/build-prompt-command.md
import * as vscode from 'vscode'
import { execSync } from 'child_process'

const MAX_DIFF_CHARS = 4_000
const MAX_SYMBOLS = 50

export interface PromptPayload {
  query: string
  prompt_type: 'QUERY' | 'GENERATE_TESTS'
  language: string
}

export async function buildPromptFromFolder(
  folderUri: vscode.Uri,
  promptType: 'QUERY' | 'GENERATE_TESTS' = 'QUERY'
): Promise<PromptPayload> {
  const pattern = new vscode.RelativePattern(folderUri, '**/*.java')
  const javaFiles = await vscode.workspace.findFiles(pattern)

  if (javaFiles.length === 0) {
    throw new Error('No .java files found in the selected folder.')
  }

  const diff = getDiff()

  // Collect symbols from each file, capped at MAX_SYMBOLS total
  const fileEntries: Array<{ name: string; symbols: vscode.DocumentSymbol[] }> = []
  let totalSymbols = 0
  for (const fileUri of javaFiles) {
    if (totalSymbols >= MAX_SYMBOLS) break
    const symbols = await getSymbols(fileUri)
    const sliced = symbols.slice(0, MAX_SYMBOLS - totalSymbols)
    fileEntries.push({ name: fileUri.fsPath.split(/[\\/]/).pop() ?? '', symbols: sliced })
    totalSymbols += sliced.length
  }

  const folderName = folderUri.fsPath.split(/[\\/]/).pop() ?? ''
  const filesSummary = fileEntries
    .map(({ name, symbols }) => {
      const syms = symbols
        .map((s) => `  ${vscode.SymbolKind[s.kind]}: ${s.name}`)
        .join('\n')
      return syms ? `File: ${name}\n${syms}` : `File: ${name}`
    })
    .join('\n\n')

  const query = [
    `Folder: ${folderName} (${javaFiles.length} Java files)`,
    filesSummary,
    diff ? `Git diff (truncated):\n${diff}` : '',
  ]
    .filter(Boolean)
    .join('\n\n')

  return { query, prompt_type: promptType, language: 'java' }
}

export async function buildPrompt(
  editor: vscode.TextEditor,
  promptType: 'QUERY' | 'GENERATE_TESTS' = 'QUERY'
): Promise<PromptPayload> {
  const [diff, symbols] = await Promise.all([
    getDiff(),
    getSymbols(editor.document.uri),
  ])

  const symbolSummary = symbols
    .slice(0, MAX_SYMBOLS)
    .map((s) => `${vscode.SymbolKind[s.kind]}: ${s.name}`)
    .join('\n')

  const fileName = editor.document.fileName.split(/[\\/]/).pop() ?? ''
  const query = [
    `File: ${fileName}`,
    symbolSummary ? `Symbols:\n${symbolSummary}` : '',
    diff ? `Git diff (truncated):\n${diff}` : '',
  ]
    .filter(Boolean)
    .join('\n\n')

  return { query, prompt_type: promptType, language: 'java' }
}

// ── Git diff ─────────────────────────────────────────────────────────────────

function getDiff(): string {
  try {
    const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
    if (!workspaceRoot) return ''
    const raw = execSync('git diff --unified=3 HEAD', {
      cwd: workspaceRoot,
      encoding: 'utf8',
      timeout: 5_000,
    })
    return raw.slice(0, MAX_DIFF_CHARS)
  } catch {
    return '' // no git repo or git not available
  }
}

// ── LSP symbols ───────────────────────────────────────────────────────────────

async function getSymbols(uri: vscode.Uri): Promise<vscode.DocumentSymbol[]> {
  try {
    const result = await vscode.commands.executeCommand<vscode.DocumentSymbol[]>(
      'vscode.executeDocumentSymbolProvider',
      uri
    )
    return flattenSymbols(result ?? [])
  } catch {
    return []
  }
}

function flattenSymbols(
  symbols: vscode.DocumentSymbol[],
  depth = 0
): vscode.DocumentSymbol[] {
  const out: vscode.DocumentSymbol[] = []
  for (const s of symbols) {
    out.push(s)
    if (depth < 2 && s.children?.length) {
      out.push(...flattenSymbols(s.children, depth + 1))
    }
  }
  return out
}
