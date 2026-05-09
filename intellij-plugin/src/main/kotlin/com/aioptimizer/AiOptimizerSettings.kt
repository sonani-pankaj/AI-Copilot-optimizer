// Settings persistence + Configurable for the IntelliJ plugin settings panel
package com.aioptimizer

import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.components.PersistentStateComponent
import com.intellij.openapi.components.Service
import com.intellij.openapi.components.State
import com.intellij.openapi.components.Storage
import com.intellij.openapi.options.Configurable
import javax.swing.JComponent
import javax.swing.JLabel
import javax.swing.JPanel
import javax.swing.JPasswordField
import javax.swing.JTextField
import java.awt.GridBagConstraints
import java.awt.GridBagLayout
import java.awt.Insets

@Service
@State(name = "AiOptimizerSettings", storages = [Storage("ai-copilot-optimizer.xml")])
class AiOptimizerSettings : PersistentStateComponent<AiOptimizerSettings.State> {

    data class State(var backendUrl: String = "http://localhost:8000")

    private var state = State()

    override fun getState() = state
    override fun loadState(s: State) { state = s }

    var backendUrl: String
        get() = state.backendUrl
        set(v) { state.backendUrl = v }

    companion object {
        fun getInstance(): AiOptimizerSettings =
            ApplicationManager.getApplication().getService(AiOptimizerSettings::class.java)
    }
}

class AiOptimizerSettingsConfigurable : Configurable {
    private lateinit var backendUrlField: JTextField
    private lateinit var tokenField: JPasswordField

    override fun getDisplayName() = "AI Copilot Optimizer"

    override fun createComponent(): JComponent {
        val settings = AiOptimizerSettings.getInstance()
        backendUrlField = JTextField(settings.backendUrl, 40)
        tokenField = JPasswordField(BackendClient.getToken() ?: "", 40)

        val panel = JPanel(GridBagLayout())
        val gbc = GridBagConstraints().apply {
            fill = GridBagConstraints.HORIZONTAL; insets = Insets(4, 4, 4, 4)
        }

        gbc.gridx = 0; gbc.gridy = 0; panel.add(JLabel("Backend URL:"), gbc)
        gbc.gridx = 1; panel.add(backendUrlField, gbc)

        gbc.gridx = 0; gbc.gridy = 1; panel.add(JLabel("JWT Token:"), gbc)
        gbc.gridx = 1; panel.add(tokenField, gbc)

        return panel
    }

    override fun isModified(): Boolean {
        val settings = AiOptimizerSettings.getInstance()
        return backendUrlField.text != settings.backendUrl ||
               String(tokenField.password) != (BackendClient.getToken() ?: "")
    }

    override fun apply() {
        AiOptimizerSettings.getInstance().backendUrl = backendUrlField.text
        val token = String(tokenField.password)
        if (token.isNotBlank()) BackendClient.storeToken(token)
    }
}
