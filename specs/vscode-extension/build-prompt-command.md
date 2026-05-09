# Spec: VS Code Extension — Build Optimized Copilot Prompt Command

## Purpose
Extracts context from the active Java file (git diff + LSP symbols), builds a structured
JSON prompt, queries the backend cache, and displays the result in a WebView panel.

## Inputs
| Source              | Value                                | Limit     |
|---------------------|--------------------------------------|-----------|
| Active editor file  | File path, language ID               | java only |
| git diff            | `git diff --unified=3 HEAD`          | 4000 chars|
| LSP symbols         | `vscode.executeDocumentSymbolProvider`| 50 items  |
| VS Code SecretStorage| JWT token                           | required  |
| Backend URL         | `ai-copilot-optimizer.backendUrl` setting | default: http://localhost:8000 |

## Outputs
WebView panel opened with:
- Prompt preview (JSON formatted)
- Cache hit/miss badge
- Buttons: Copy, Regenerate, Generate Tests

## Behavior / Logic
1. **Trigger**: command `ai-copilot-optimizer.buildPrompt` OR `onSave` for `*.java` files
2. Check `languageId === 'java'` — skip silently for non-Java files
3. Retrieve JWT from SecretStorage; if absent → show error message with "Please login first"
4. Run `git diff --unified=3 HEAD` in workspace root; truncate to 4000 chars
5. Call `vscode.executeDocumentSymbolProvider(uri)` → extract name+kind; limit to first 50
6. Build payload: `{ query: symbolSummary + diff, prompt_type: "QUERY", language: "java" }`
7. POST to `{backendUrl}/query` with `Authorization: Bearer {jwt}`
8. Open / update WebView panel with response
9. Show loading spinner in panel during fetch

## Acceptance Criteria
- [ ] Command appears in Command Palette as "Build Optimized Copilot Prompt"
- [ ] Auto-runs on save of `.java` files only
- [ ] Diff truncated at 4000 chars (no error thrown)
- [ ] Symbols limited to 50
- [ ] Panel opens with response + cache hit/miss indicator
- [ ] Copy button copies response text to clipboard
- [ ] Generate Tests button sends `prompt_type: "GENERATE_TESTS"` and updates panel

## Edge Cases
- No git repo in workspace → skip diff, proceed with symbols only
- JWT expired (401 from backend) → show "Session expired. Please login." in panel
- Backend unreachable → show "Backend offline. Start with docker-compose up." in panel

## Dependencies
- `src/backendClient.ts`
- `src/webviewPanel.ts`
- `src/promptBuilder.ts`
- `specs/backend/query-endpoint.md`
