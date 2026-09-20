package pl.radiodrive.app.data

import android.content.Context
import org.json.JSONArray

class UserLibrary(context: Context) {
    private val prefs = context.getSharedPreferences("radio_library", Context.MODE_PRIVATE)

    fun favorites(): Set<String> = prefs.getStringSet(KEY_FAVORITES, emptySet())?.toSet().orEmpty()

    fun toggleFavorite(id: String): Boolean {
        val updated = favorites().toMutableSet()
        val nowFavorite = if (updated.remove(id)) false else {
            updated.add(id)
            true
        }
        prefs.edit().putStringSet(KEY_FAVORITES, updated).apply()
        return nowFavorite
    }

    fun rememberRecent(id: String) {
        val current = recent().toMutableList()
        current.remove(id)
        current.add(0, id)
        prefs.edit().putString(KEY_RECENT, current.take(MAX_RECENT).joinToString("|")).apply()
    }

    fun recent(): List<String> = prefs.getString(KEY_RECENT, "")
        .orEmpty()
        .split('|')
        .filter { it.isNotBlank() }

    fun rememberTrack(stationId: String, text: String) {
        val clean = text.trim()
        if (clean.isBlank()) return
        val current = trackHistory(stationId).toMutableList()
        if (current.firstOrNull().equals(clean, ignoreCase = true)) return
        current.removeAll { it.equals(clean, ignoreCase = true) }
        current.add(0, clean)
        val json = JSONArray()
        current.take(MAX_TRACKS).forEach(json::put)
        prefs.edit().putString("tracks_$stationId", json.toString()).apply()
    }

    fun trackHistory(stationId: String): List<String> = runCatching {
        val raw = prefs.getString("tracks_$stationId", "[]") ?: "[]"
        val json = JSONArray(raw)
        buildList {
            for (i in 0 until json.length()) add(json.optString(i))
        }.filter { it.isNotBlank() }
    }.getOrDefault(emptyList())

    companion object {
        private const val KEY_FAVORITES = "favorites"
        private const val KEY_RECENT = "recent"
        private const val MAX_RECENT = 20
        private const val MAX_TRACKS = 12
    }
}
