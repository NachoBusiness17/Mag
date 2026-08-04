package com.mag.remote.net

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit

/**
 * DeepSeek direct client for the Android remote app.
 *
 * LIVE-VERIFIED against https://api.deepseek.com (2026-08-02).
 *
 * Cost-conscious defaults baked in:
 *  - thinking OFF by default -> ~15x cheaper (7 vs 103 tokens for "Say OK").
 *    Reasoning tokens count against max_tokens, so a small max_tokens with
 *    thinking ON can return an EMPTY reply.
 *  - `thinking` is a TOP-LEVEL body param (not extra_body — SDK-only concept).
 *  - Canonical model names: deepseek-v4-flash / deepseek-v4-pro.
 *    (deepseek-chat / deepseek-reasoner are legacy aliases.)
 *  - user_id isolates per-tablet KVCache / scheduling (regex [a-zA-Z0-9\-_]+).
 */
class DeepSeekClient(
    private val apiKey: String,
    private val baseUrl: String = "https://api.deepseek.com",
) {
    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(120, TimeUnit.SECONDS)
        .build()

    data class ChatResult(
        val reply: String,
        val reasoning: String,
        val model: String,
        val promptTokens: Int,
        val completionTokens: Int,
    )

    /**
     * Chat Completions with thinking-off default.
     *
     * @param thinking set true only for deep reasoning; then raise [maxTokens]
     *   to leave room for reasoning tokens (they count against max_tokens).
     * @param userId optional per-tablet identity for KVCache/scheduling isolation.
     */
    suspend fun chat(
        user: String,
        system: String? = null,
        model: String = MODEL_FLASH,
        thinking: Boolean = false,
        reasoningEffort: String = "low",
        maxTokens: Int = 512,
        userId: String? = null,
    ): ChatResult = withContext(Dispatchers.IO) {
        val messages = JSONArray()
        if (system != null) {
            messages.put(JSONObject().put("role", "system").put("content", system))
        }
        messages.put(JSONObject().put("role", "user").put("content", user))

        val body = JSONObject()
            .put("model", model)
            .put("messages", messages)
            .put("max_tokens", maxTokens)
            .put("thinking", JSONObject().put("type", if (thinking) "enabled" else "disabled"))
        if (thinking) body.put("reasoning_effort", reasoningEffort)
        if (userId != null) body.put("user_id", userId)

        val req = Request.Builder()
            .url("$baseUrl/v1/chat/completions")
            .header("Authorization", "Bearer $apiKey")
            .header("Content-Type", "application/json")
            .post(body.toString().toRequestBody("application/json".toMediaType()))
            .build()

        client.newCall(req).execute().use { resp ->
            val text = resp.body?.string() ?: ""
            if (!resp.isSuccessful) {
                throw RuntimeException("DeepSeek HTTP ${resp.code}: ${text.take(300)}")
            }
            val json = JSONObject(text)
            val msg = json.getJSONArray("choices").getJSONObject(0).getJSONObject("message")
            val usage = json.optJSONObject("usage")
            ChatResult(
                reply = msg.optString("content", ""),
                reasoning = msg.optString("reasoning_content", ""),
                model = json.optString("model", model),
                promptTokens = usage?.optInt("prompt_tokens", 0) ?: 0,
                completionTokens = usage?.optInt("completion_tokens", 0) ?: 0,
            )
        }
    }

    companion object {
        const val MODEL_FLASH = "deepseek-v4-flash"
        const val MODEL_PRO = "deepseek-v4-pro"
    }
}
