# Spec: IntelliJ Plugin — AI Prompt Tool Window

## Purpose
Persistent side panel (tool window) that shows the extracted prompt, backend response,
and cache metadata. Stays open across file switches.

## Inputs (set programmatically by BuildAiPromptAction)
| State     | Description                                  |
|-----------|----------------------------------------------|
| IDLE      | Initial state, shows "Run Build AI Prompt"   |
| LOADING   | Spinner shown, buttons disabled              |
| RESULT    | Response text + cache hit/miss badge         |
| ERROR     | Error message + Retry button                 |

## Outputs
- Visual tool window docked to right side panel
- Copy button → writes response to system clipboard
- Retry button → re-triggers BuildAiPromptAction

## Behavior / Logic
1. Tool window registered in `plugin.xml` as `AiPromptToolWindowFactory`
2. Renders a single `JPanel` with:
   - Status label (IDLE / LOADING / RESULT / ERROR)
   - Cache badge: green label "Cache Hit" or yellow label "OpenAI"
   - JTextArea (read-only, word-wrap) for response text
   - Toolbar with Copy and Retry buttons
3. All UI updates must be called on EDT (`ApplicationManager.getApplication().invokeLater`)
4. Copy button: `Toolkit.getDefaultToolkit().systemClipboard.setContents(...)`

## Acceptance Criteria
- [ ] Tool window visible in View → Tool Windows menu
- [ ] LOADING state shows spinner, disables buttons
- [ ] RESULT state shows response text and correct badge color
- [ ] ERROR state shows error message and Retry button
- [ ] Copy button puts response in system clipboard
- [ ] Tool window persists between file switches

## Edge Cases
- Empty response from backend → show "Empty response received"
- Response > 5000 chars → display truncated with "... (truncated)" note

## Dependencies
- `BuildAiPromptAction.kt` (calls `setState` on tool window)
- `plugin.xml` (tool window factory registration)
- `specs/intellij-plugin/build-prompt-action.md`
