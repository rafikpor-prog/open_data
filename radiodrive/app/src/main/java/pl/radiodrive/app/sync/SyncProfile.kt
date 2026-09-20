package pl.radiodrive.app.sync

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import pl.radiodrive.app.data.StationRepository

object SyncClock {
    private const val PREFS = "radiodrive_sync_clock"
    private const val KEY_UPDATED = "profile_updated_at"

    fun touch(context: Context): Long {
        val value = System.currentTimeMillis()
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putLong(KEY_UPDATED, value).apply()
        return value
    }

    fun updatedAt(context: Context): Long {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val current = prefs.getLong(KEY_UPDATED, 0L)
        if (current > 0L) return current
        return touch(context)
    }

    fun set(context: Context, value: Long) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putLong(KEY_UPDATED, value.coerceAtLeast(1L)).apply()
    }
}

object SyncProfileStore {
    private const val STATION_PREFS = "station_overrides"
    private const val LIBRARY_PREFS = "radio_library"

    fun export(context: Context): JSONObject {
        val root = JSONObject()
            .put("schema", 1)
            .put("updatedAt", SyncClock.updatedAt(context))

        val stationPrefs = context.getSharedPreferences(STATION_PREFS, Context.MODE_PRIVATE)
        val stationOverrides = JSONObject()
        stationPrefs.all.forEach { (key, value) ->
            if (value is String) {
                stationOverrides.put(
                    key,
                    runCatching { JSONObject(value) }.getOrElse { value }
                )
            }
        }
        root.put("stationOverrides", stationOverrides)

        val library = context.getSharedPreferences(LIBRARY_PREFS, Context.MODE_PRIVATE)
        val favorites = JSONArray()
        library.getStringSet("favorites", emptySet()).orEmpty().sorted().forEach(favorites::put)
        root.put("favorites", favorites)
        root.put("recent", library.getString("recent", "").orEmpty())

        return root
    }

    fun import(context: Context, root: JSONObject) {
        val stationPrefs = context.getSharedPreferences(STATION_PREFS, Context.MODE_PRIVATE)
        val stationEditor = stationPrefs.edit().clear()
        val overrides = root.optJSONObject("stationOverrides") ?: JSONObject()
        val keys = overrides.keys()
        while (keys.hasNext()) {
            val id = keys.next()
            val value = overrides.opt(id)
            when (value) {
                is JSONObject -> stationEditor.putString(id, value.toString())
                is String -> stationEditor.putString(id, value)
            }
        }
        stationEditor.apply()

        val library = context.getSharedPreferences(LIBRARY_PREFS, Context.MODE_PRIVATE)
        val favorites = buildSet {
            val array = root.optJSONArray("favorites") ?: JSONArray()
            for (i in 0 until array.length()) {
                array.optString(i).takeIf { it.isNotBlank() }?.let(::add)
            }
        }
        library.edit()
            .putStringSet("favorites", favorites)
            .putString("recent", root.optString("recent"))
            .apply()

        SyncClock.set(context, root.optLong("updatedAt", System.currentTimeMillis()))
        StationRepository.get(context).reloadOverrides()
    }
}
