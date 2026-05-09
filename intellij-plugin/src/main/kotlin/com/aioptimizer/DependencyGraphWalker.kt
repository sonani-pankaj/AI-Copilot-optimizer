// See: specs/intellij-plugin/build-prompt-action.md
package com.aioptimizer

import com.intellij.openapi.application.ReadAction
import com.intellij.psi.JavaPsiFacade
import com.intellij.psi.PsiClass
import com.intellij.psi.PsiFile
import com.intellij.psi.PsiJavaFile
import com.intellij.psi.search.GlobalSearchScope

object DependencyGraphWalker {

    fun walk(file: PsiFile, maxNodes: Int = 30): List<String> {
        if (file !is PsiJavaFile) return emptyList()

        val deps = mutableSetOf<String>()
        ReadAction.run<Throwable> {
            val project = file.project
            val facade = JavaPsiFacade.getInstance(project)
            val scope = GlobalSearchScope.allScope(project)

            for (import in file.importList?.importStatements ?: emptyArray()) {
                val qualifiedName = import.qualifiedName ?: continue
                if (deps.size >= maxNodes) break
                // Resolve to class and extract first-level dependencies
                val cls = facade.findClass(qualifiedName, scope)
                if (cls != null) {
                    deps.add(qualifiedName)
                    cls.superTypes
                        .take(maxNodes - deps.size)
                        .mapNotNullTo(deps) { it.canonicalText.takeIf { n -> !n.startsWith("java.") } }
                }
            }
        }

        return deps.take(maxNodes).toList()
    }
}
