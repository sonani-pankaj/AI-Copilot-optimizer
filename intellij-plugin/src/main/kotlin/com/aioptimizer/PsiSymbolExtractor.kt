// See: specs/intellij-plugin/build-prompt-action.md
package com.aioptimizer

import com.intellij.psi.PsiClass
import com.intellij.psi.PsiFile
import com.intellij.psi.PsiMethod
import com.intellij.psi.PsiRecursiveElementVisitor
import com.intellij.openapi.application.ReadAction

data class ExtractedSymbol(val kind: String, val name: String, val signature: String)

object PsiSymbolExtractor {

    private const val MAX_SYMBOLS = 50

    fun extract(file: PsiFile): List<ExtractedSymbol> {
        val symbols = mutableListOf<ExtractedSymbol>()

        ReadAction.run<Throwable> {
            file.accept(object : PsiRecursiveElementVisitor() {
                override fun visitElement(element: com.intellij.psi.PsiElement) {
                    if (symbols.size >= MAX_SYMBOLS) return
                    when (element) {
                        is PsiClass -> {
                            symbols.add(
                                ExtractedSymbol(
                                    kind = if (element.isInterface) "Interface"
                                           else if (element.isEnum) "Enum"
                                           else "Class",
                                    name = element.name ?: "<anon>",
                                    signature = element.qualifiedName ?: element.name ?: "<anon>"
                                )
                            )
                        }
                        is PsiMethod -> {
                            symbols.add(
                                ExtractedSymbol(
                                    kind = if (element.isConstructor) "Constructor" else "Method",
                                    name = element.name,
                                    signature = buildMethodSignature(element)
                                )
                            )
                        }
                    }
                    if (symbols.size < MAX_SYMBOLS) super.visitElement(element)
                }
            })
        }

        return symbols.take(MAX_SYMBOLS)
    }

    private fun buildMethodSignature(method: PsiMethod): String {
        val params = method.parameterList.parameters.joinToString(", ") {
            "${it.type.presentableText} ${it.name}"
        }
        val returnType = method.returnType?.presentableText ?: "void"
        return "$returnType ${method.name}($params)"
    }
}
