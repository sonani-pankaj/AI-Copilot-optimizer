// See: specs/intellij-plugin/build-prompt-action.md
package com.aioptimizer

import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.CommonDataKeys
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.project.Project
import com.intellij.openapi.wm.ToolWindowManager

class BuildAiPromptAction : AnAction() {

    override fun actionPerformed(e: AnActionEvent) {
        val project: Project = e.project ?: return
        val editor = e.getData(CommonDataKeys.EDITOR) ?: return
        val psiFile = e.getData(CommonDataKeys.PSI_FILE) ?: return

        // Only act on Java files
        if (psiFile.language.id != "JAVA") return

        val toolWindowManager = ToolWindowManager.getInstance(project)
        val toolWindow = toolWindowManager.getToolWindow("AI Copilot Optimizer") ?: return
        toolWindow.show()

        val content = toolWindow.contentManager.selectedContent ?: return
        val ui = content.component as? AiPromptToolWindow ?: return
        ui.setLoading(true)

        ApplicationManager.getApplication().executeOnPooledThread {
            try {
                val symbols = PsiSymbolExtractor.extract(psiFile)
                val deps = DependencyGraphWalker.walk(psiFile, maxNodes = 30)
                val diff = GitDiffUtil.getDiff(project, maxChars = 4_000)

                val payload = BackendClient.buildPayload(
                    symbols = symbols,
                    dependencies = deps,
                    diff = diff,
                    promptType = "QUERY",
                    language = "java"
                )

                val result = BackendClient.query(project, payload)

                ApplicationManager.getApplication().invokeLater {
                    ui.setResult(result)
                }
            } catch (ex: Exception) {
                ApplicationManager.getApplication().invokeLater {
                    ui.setError(ex.message ?: "Unknown error")
                }
            }
        }
    }

    override fun update(e: AnActionEvent) {
        val psiFile = e.getData(CommonDataKeys.PSI_FILE)
        e.presentation.isEnabled = psiFile?.language?.id == "JAVA"
    }
}
