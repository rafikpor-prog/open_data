package pl.radiodrive.app.data

import android.content.Context
import pl.radiodrive.app.sync.SyncClock

class HiddenStations(private val context: Context) {
    private val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    fun all(): Set<String> = prefs.getStringSet(KEY_IDS, emptySet())?.toSet().orEmpty()

    fun hide(id: String) {
        if (id.isBlank()) return
        val updated = all().toMutableSet()
        if (updated.add(id)) {
            prefs.edit().putStringSet(KEY_IDS, updated).apply()
            SyncClock.touch(context)
        }
    }

    fun restore(id: String) {
        val updated = all().toMutableSet()
        if (updated.remove(id)) {
            prefs.edit().putStringSet(KEY_IDS, updated).apply()
            SyncClock.touch(context)
        }
    }

    fun clear() {
        if (all().isEmpty()) return
        prefs.edit().remove(KEY_IDS).apply()
        SyncClock.touch(context)
    }

    companion object {
        const val PREFS = "hidden_stations"
        const val KEY_IDS = "ids"
    }
}
