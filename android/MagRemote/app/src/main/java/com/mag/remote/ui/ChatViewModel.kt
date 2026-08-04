package com.mag.remote.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mag.remote.data.SettingsStore
import com.mag.remote.net.DeepSeekClient
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

data class ChatMessage(
    val role: String, // "user" | "assistant"
    val text: String,
    val reasoning: String = "",
)

data class ChatUiState(
    val messages: List<ChatMessage> = emptyList(),
    val input: String = "",
    val busy: Boolean = false,
    val error: String? = null,
    val thinking: Boolean = false,
    val model: String = DeepSeekClient.MODEL_FLASH,
    val lastTokens: String = "",
)

/**
 * Chat ViewModel — drives the DeepSeek direct client (thinking-off default).
 * Falls back to the Mag gateway if DeepSeek key is absent.
 */
class ChatViewModel(
    private val settings: SettingsStore,
) : ViewModel() {

    private val _state = MutableStateFlow(ChatUiState())
    val state: StateFlow<ChatUiState> = _state

    private val deepSeek: DeepSeekClient? by lazy {
        settings.deepSeekKey.takeIf { it.isNotBlank() }?.let { DeepSeekClient(it) }
    }

    fun onInputChange(v: String) {
        _state.value = _state.value.copy(input = v)
    }

    fun toggleThinking() {
        _state.value = _state.value.copy(thinking = !_state.value.thinking)
    }

    fun switchModel() {
        val next = if (_state.value.model == DeepSeekClient.MODEL_FLASH) {
            DeepSeekClient.MODEL_PRO
        } else {
            DeepSeekClient.MODEL_FLASH
        }
        _state.value = _state.value.copy(model = next)
    }

    fun send() {
        val text = _state.value.input.trim()
        if (text.isEmpty() || _state.value.busy) return

        val client = deepSeek
        if (client == null) {
            _state.value = _state.value.copy(error = "DeepSeek key not set — configure in Settings.")
            return
        }

        val userMsg = ChatMessage("user", text)
        _state.value = _state.value.copy(
            messages = _state.value.messages + userMsg,
            input = "",
            busy = true,
            error = null,
        )

        viewModelScope.launch {
            try {
                val r = client.chat(
                    user = text,
                    model = _state.value.model,
                    thinking = _state.value.thinking,
                    maxTokens = if (_state.value.thinking) 2048 else 512,
                    userId = settings.userId,
                )
                val assistant = ChatMessage(
                    role = "assistant",
                    text = r.reply,
                    reasoning = r.reasoning,
                )
                _state.value = _state.value.copy(
                    messages = _state.value.messages + assistant,
                    busy = false,
                    lastTokens = "in=${r.promptTokens} out=${r.completionTokens}",
                )
            } catch (e: Exception) {
                _state.value = _state.value.copy(
                    busy = false,
                    error = e.message ?: "DeepSeek call failed",
                )
            }
        }
    }
}
