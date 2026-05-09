// See: specs/intellij-plugin/build-prompt-action.md

plugins {
    id("org.jetbrains.intellij.platform") version "2.1.0"
    kotlin("jvm") version "1.9.25"
}

group = "com.aioptimizer"
version = "1.0.0"

repositories {
    mavenCentral()
    intellijPlatform {
        defaultRepositories()
    }
}

dependencies {
    intellijPlatform {
        intellijIdeaCommunity("2024.1")
        pluginVerifier()
        zipSigner()
        instrumentationTools()
    }
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")
    implementation("com.fasterxml.jackson.module:jackson-module-kotlin:2.17.0")
    implementation("com.fasterxml.jackson.core:jackson-databind:2.17.0")
}

intellijPlatform {
    pluginConfiguration {
        id.set("com.aioptimizer.plugin")
        name.set("AI Copilot Optimizer")
        version.set("1.0.0")
        description.set("Reduces token usage for Java monolith AI queries via semantic cache")
        ideaVersion {
            sinceBuild.set("241")
        }
    }
    publishing {
        token.set(System.getenv("PUBLISH_TOKEN") ?: "")
    }
}

kotlin {
    jvmToolchain(17)
}
