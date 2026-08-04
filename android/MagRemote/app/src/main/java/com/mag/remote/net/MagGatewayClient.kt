package com.mag.remote.net

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit

/**
 * Thin client for the local Mag FastAPI gateway.
 *
 * Contract (mag/api_gateway.py + mag/api_server.py):
 *  - Every route gated by X-API-Key header (constant-time compare).
 *  - Envelope: {"ok": bool, "schema": str, "data": ...} on success,
 *    {"ok": false, "error": str} on failure.
 *  - Default host 127.0.0.1:8000 (LAN IP or tunnel URL for remote).
 *
 * NOTE: the gateway registry currently has no concrete routes registered
 * (it is the foundation only). The dashboard/rest.py surface (health,
 * mag_os, home_summary) is the richer API. This client targets the gateway
 * contract; extend with concrete paths as routes are registered.
 */
class MagGatewayClient(
    private val baseUrl: String,
    private val apiKey: String,
) {
    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .build()

    /** GET a gateway path. Returns the parsed envelope. */
    suspend fun get(path: String): JSONObject = withContext(Dispatchers.IO) {
        val req = Request.Builder()
            .url("$baseUrl$path")
            .header("X-API-Key", apiKey)
            .get()
            .build()
        client.newCall(req).execute().use { resp ->
            val text = resp.body?.string() ?: ""
            if (!resp.isSuccessful) {
                throw RuntimeException("Mag HTTP ${resp.code}: ${text.take(300)}")
            }
            JSONObject(text)
        }
    }

    /** POST a gateway path with a JSON body. */
    suspend fun post(path: String, body: JSONObject): JSONObject = withContext(Dispatchers.IO) {
        val req = Request.Builder()
            .url("$baseUrl$path")
            .header("X-API-Key", apiKey)
            .header("Content-Type", "application/json")
            .post(body.toString().toRequestBody("application/json".toMediaType()))
            .build()
        client.newCall(req).execute().use { resp ->
            val text = resp.body?.string() ?: ""
            if (!resp.isSuccessful) {
                throw RuntimeException("Mag HTTP ${resp.code}: ${text.take(300)}")
            }
            JSONObject(text)
        }
    }

    /** Health check — returns ok:true if the gateway is reachable + key valid. */
    suspend fun health(): Boolean = try {
        get("/health").optBoolean("ok", false)
    } catch (e: Exception) {
        false
    }
}
