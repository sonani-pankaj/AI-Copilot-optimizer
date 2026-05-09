// Git diff utility for IntelliJ plugin
package com.aioptimizer

import com.intellij.openapi.project.Project
import com.intellij.openapi.vcs.VcsException
import com.intellij.openapi.vcs.changes.ChangeListManager

object GitDiffUtil {
    fun getDiff(project: Project, maxChars: Int = 4_000): String {
        return try {
            val manager = ChangeListManager.getInstance(project)
            val sb = StringBuilder()
            for (change in manager.allChanges) {
                if (sb.length >= maxChars) break
                val path = change.virtualFile?.path ?: continue
                if (!path.endsWith(".java")) continue
                sb.appendLine("--- ${change.virtualFile?.name}")
            }
            sb.toString().take(maxChars)
        } catch (_: VcsException) {
            ""
        }
    }
}
