package pl.radiodrive.app.data

import android.content.Context

class UserLibrary(context: Context) {
    private val prefs = context.getSharedPreferences("radio_library", Context.MODE_PRIVATE)

    fun isFavorite(id: String): Boolean = id in favorites()

    fun favorites(): Set<String> = prefs.getStringSet(KEY_FAVORITES, emptySet())?.toSet().orEmpty()

    fun toggleFavorite(id: String): Boolean {
        val updated = favorites().toMutableSet()
        val nowFavorite = if (id in updated) {
            updated.remove(id)
            false
        } else {
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

    companion object {
        private const val KEY_FAVORITES = "favorites"
        private const val KEY_RECENT = "recent"
        private const val MAX_RECENT = 12
    }
}
