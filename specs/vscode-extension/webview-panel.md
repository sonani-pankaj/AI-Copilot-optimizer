# Spec: VS Code Extension — WebView Panel

## Purpose
Renders the AI response and cache metadata inside a VS Code WebView panel.
Handles user interactions (Copy, Regenerate, Generate Tests) via message passing.

## Inputs (from extension host → WebView)
```typescript
{ type: 'update', payload: { response: string, cacheHit: boolean, similarity?: number, loading: boolean } }
{ type: 'error', payload: { message: string } }
```

## Outputs (from WebView → extension host via postMessage)
```typescript
{ type: 'copy' }
{ type: 'regenerate' }
{ type: 'generateTests' }
```

## Behavior / Logic
1. Panel opens/reveals on column beside active editor
2. While `loading = true` → show spinner, disable buttons
3. Cache hit badge: green "Cache Hit ✓" if `cacheHit=true`, yellow "OpenAI Response" if false
4. Similarity score shown only when `similarity` is present
5. Response rendered in `<pre>` block with monospace font
6. Copy button: `postMessage({ type: 'copy' })` → extension host copies to clipboard
7. Regenerate button: `postMessage({ type: 'regenerate' })` → extension re-runs query
8. Generate Tests button: `postMessage({ type: 'generateTests' })` → re-runs with GENERATE_TESTS type
9. Panel title: "AI Copilot Optimizer"
10. Panel icon: uses `$(robot)` codicon

## Acceptance Criteria
- [ ] Loading spinner visible during fetch
- [ ] Cache hit badge correct color (green/yellow)
- [ ] Response text visible in pre block
- [ ] Copy sends correct postMessage
- [ ] Regenerate re-triggers prompt build
- [ ] Generate Tests sends GENERATE_TESTS prompt_type
- [ ] Panel persists (does not close) on file switch

## Edge Cases
- Very long response → panel scrollable, not clipped
- Error state → error message shown, all action buttons hidden except Regenerate

## Dependencies
- `src/extension.ts` (message handler)
- `specs/vscode-extension/build-prompt-command.md`
