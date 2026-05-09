# Spec: IntelliJ Plugin — Build AI Prompt Action

## Purpose
Analyzes the currently open Java file using PSI, extracts Spring-annotated symbols,
expands a dependency graph (BFS depth 2), builds a structured prompt, and sends it
to the FastAPI backend.

## Inputs
| Source            | Value                                          | Limit  |
|-------------------|------------------------------------------------|--------|
| Active PSI file   | PsiJavaFile in editor                          | —      |
| PSI visitor       | Classes/methods with Spring annotations        | 50     |
| BFS dep graph     | Imports + PSI references, depth 2              | 30     |
| PasswordSafe      | JWT token (key: "ai-copilot-optimizer")        | req.   |
| Settings          | Backend URL (default: http://localhost:8000)   | —      |

## Outputs
Tool window updated with:
- Extracted symbols JSON
- Backend response (cache hit/miss)
- Copy to clipboard button

## Behavior / Logic
1. **Trigger**: Tools menu → "Build AI Prompt" or keyboard shortcut
2. Check active editor has PsiJavaFile; show error balloon if not Java
3. Run PSI visitor (ReadAction) to collect:
   - Classes annotated with `@RestController`, `@Service`, `@Repository`
   - Methods inside those classes (name + param types)
   - Spring Batch: classes with `@Configuration` containing `@Bean` methods returning `Job` or `Step`
4. Run BFS dependency walker from collected classes, depth=2, cap at 30 nodes
5. Build prompt payload: `{ query: symbolsJson, prompt_type: "QUERY", language: "java" }`
6. Retrieve JWT from PasswordSafe; if absent → show balloon "Configure JWT in Settings"
7. POST to `{backendUrl}/query` asynchronously (background thread, not EDT)
8. On response: update tool window content on EDT via `invokeLater`

## Acceptance Criteria
- [ ] `@RestController` class → extracted and shown in tool window
- [ ] `@Service` class → extracted
- [ ] `@Repository` class → extracted
- [ ] BFS walker does not exceed depth 2 or 30 nodes
- [ ] Tool window shows cache hit/miss badge
- [ ] Copy button copies response JSON to clipboard
- [ ] Non-Java file → shows error balloon (no crash)

## Edge Cases
- File with no Spring annotations → sends empty symbols array, still calls backend
- Backend unreachable → show "Backend offline" in tool window
- JWT missing → show balloon, do not make HTTP call

## Dependencies
- `PsiSymbolExtractor.kt`
- `DependencyGraphWalker.kt`
- `BackendClient.kt`
- `AiPromptToolWindow.kt`
- `specs/backend/query-endpoint.md`
