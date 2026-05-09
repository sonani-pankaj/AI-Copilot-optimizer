// See: specs/intellij-plugin/tool-window.md
package com.aioptimizer

import com.intellij.openapi.project.Project
import com.intellij.openapi.wm.ToolWindow
import com.intellij.openapi.wm.ToolWindowFactory
import com.intellij.ui.content.ContentFactory
import com.intellij.ui.components.JBScrollPane
import java.awt.BorderLayout
import java.awt.Color
import java.awt.FlowLayout
import java.awt.Font
import java.awt.Toolkit
import java.awt.datatransfer.StringSelection
import javax.swing.JButton
import javax.swing.JLabel
import javax.swing.JPanel
import javax.swing.JTextArea
import javax.swing.SwingUtilities

data class QueryResult(
    val response: String,
    val cache_hit: Boolean,
    val similarity: Double?,
    val tokens_used: Int,
)

class AiPromptToolWindowFactory : ToolWindowFactory {
    override fun createToolWindowContent(project: Project, toolWindow: ToolWindow) {
        val ui = AiPromptToolWindow()
        val content = ContentFactory.getInstance().createContent(ui, "", false)
        toolWindow.contentManager.addContent(content)
    }
}

class AiPromptToolWindow : JPanel(BorderLayout()) {

    private val statusLabel = JLabel("Ready — trigger via Ctrl+Alt+A or right-click menu")
    private val responseArea = JTextArea().apply {
        isEditable = false
        lineWrap = true
        wrapStyleWord = true
        background = Color(0x1a1d27)
        foreground = Color(0xa5f3a5)
        font = Font(Font.MONOSPACED, Font.PLAIN, 12)
    }
    private val copyButton = JButton("Copy").apply {
        isEnabled = false
        addActionListener {
            val sel = StringSelection(responseArea.text)
            Toolkit.getDefaultToolkit().systemClipboard.setContents(sel, sel)
        }
    }

    init {
        val topPanel = JPanel(BorderLayout()).apply {
            add(statusLabel, BorderLayout.CENTER)
        }
        val buttonPanel = JPanel(FlowLayout(FlowLayout.LEFT)).apply {
            add(copyButton)
        }
        add(topPanel, BorderLayout.NORTH)
        add(JBScrollPane(responseArea), BorderLayout.CENTER)
        add(buttonPanel, BorderLayout.SOUTH)
    }

    fun setLoading(loading: Boolean) {
        SwingUtilities.invokeLater {
            if (loading) {
                statusLabel.text = "⏳ Querying backend…"
                responseArea.text = ""
                copyButton.isEnabled = false
            }
        }
    }

    fun setResult(result: QueryResult) {
        SwingUtilities.invokeLater {
            val hitLabel = if (result.cache_hit) "✓ Cache Hit" else "○ LLM fallback"
            val simLabel = result.similarity?.let { " | sim: ${"%.1f".format(it * 100)}%" } ?: ""
            statusLabel.text = "$hitLabel$simLabel | tokens: ${result.tokens_used}"
            responseArea.text = result.response
            copyButton.isEnabled = true
        }
    }

    fun setError(message: String) {
        SwingUtilities.invokeLater {
            statusLabel.text = "⚠ Error"
            responseArea.text = "Error: $message"
            responseArea.foreground = Color(0xf87171)
            copyButton.isEnabled = false
        }
    }
}
