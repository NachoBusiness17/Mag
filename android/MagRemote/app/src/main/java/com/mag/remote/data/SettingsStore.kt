package com.mag.remote.data

import android.content.Context
import android.content.SharedPreferences

/**
 * Stores connection settings (Mag gateway + DeepSeek key) locally.
 * Keys are stored in plain SharedPreferences for the PoC; for production
 * consider Android Keystore / EncryptedSharedPreferences.
 */
class SettingsStore(context: Context) {
    private val prefs: SharedPreferences =
        context.getSharedPreferences("mag_remote", Context.MODE_PRIVATE)

    var magBaseUrl: String
        get() = prefs.getString(KEY_MAG_URL, "http://127.0.0.1:8000") ?: "http://127.0.0.1:8000"
        set(v) = prefs.edit().putString(KEY_MAG_URL, v).apply()

    var magApiKey: String
        get() = prefs.getString(KEY_MAG_KEY, "") ?: ""
        set(v) = prefs.edit().putString(KEY_MAG_KEY, v).apply()

    var deepSeekKey: String
        get() = prefs.getString(KEY_DS_KEY, "") ?: ""
        set(v) = prefs.edit().putString(KEY_DS_KEY, v).apply()

    var userId: String
        get() = prefs.getString(KEY_USER_ID, "mag-tablet") ?: "mag-tablet"
        set(v) = prefs.edit().putString(KEY_USER_ID, v).apply()

    companion object {
        private const val KEY_MAG_URL = "mag_base_url"
        private const val KEY_MAG_KEY = "mag_api_key"
        private const val KEY_DS_KEY = "deepseek_api_key"
        private const val KEY_USER_ID = "user_id"
    }
}
