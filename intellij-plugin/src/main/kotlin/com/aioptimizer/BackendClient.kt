// See: specs/intellij-plugin/build-prompt-action.md
package com.aioptimizer

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.module.kotlin.registerKotlinModule
import com.intellij.credentialStore.CredentialAttributes
import com.intellij.credentialStore.generateServiceName
import com.intellij.ide.passwordSafe.PasswordSafe
import com.intellij.openapi.project.Project
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit

private val JSON_MEDIA_TYPE = "application/json; charset=utf-8".toMediaType()
private val mapper = ObjectMapper().registerKotlinModule()

object BackendClient {

    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .build()

    private fun getCredentialAttributes() = CredentialAttributes(
        generateServiceName("AiCopilotOptimizer", "jwt")
    )

    fun getToken(): String? =
        PasswordSafe.instance.getPassword(getCredentialAttributes())

    fun storeToken(token: String) {
        val attrs = getCredentialAttributes()
        PasswordSafe.instance.setPassword(attrs, token)
    }

    fun buildPayload(
        symbols: List<ExtractedSymbol>,
        dependencies: List<String>,
        diff: String,
        promptType: String,
        language: String,
    ): Map<String, Any> {
        val symbolText = symbols.joinToString("\n") { "${it.kind}: ${it.signature}" }
        val depText = dependencies.take(30).joinToString("\n")
        val query = buildString {
            if (symbolText.isNotBlank()) appendLine("Symbols:\n$symbolText")
            if (depText.isNotBlank()) appendLine("Dependencies:\n$depText")
            if (diff.isNotBlank()) appendLine("Git diff:\n$diff")
        }.trim()

        return mapOf(
            "query" to query,
            "prompt_type" to promptType,
            "language" to language,
        )
    }

    fun query(project: Project, payload: Map<String, Any>): QueryResult {
        val token = getToken() ?: throw IllegalStateException(
            "No JWT token stored. Set one via the AI Copilot Optimizer settings."
        )

        // Read backend URL from project settings (falls back to default)
        val settings = AiOptimizerSettings.getInstance()
        val url = "${settings.backendUrl.trimEnd('/')}/query"

        val body = mapper.writeValueAsString(payload).toRequestBody(JSON_MEDIA_TYPE)
        val request = Request.Builder()
            .url(url)
            .post(body)
            .header("Authorization", "Bearer $token")
            .build()

        client.newCall(request).execute().use { response ->
            val raw = response.body?.string() ?: ""
            if (response.code == 401) {
                throw SecurityException("Unauthorized — please update your JWT token in settings")
            }
            if (!response.isSuccessful) {
                throw RuntimeException("Backend error ${response.code}: $raw")
            }
            return mapper.readValue(raw, QueryResult::class.java)
        }
    }
}
