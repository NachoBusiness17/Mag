# MagRemote proguard rules (release). Keep JSON + OkHttp defaults.
-keep class org.json.** { *; }
-dontwarn okhttp3.**
-dontwarn okio.**
