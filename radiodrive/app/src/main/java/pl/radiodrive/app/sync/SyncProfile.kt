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
    private const val CUSTOM_PREFS = "custom_stations"
    private const val HIDDEN_PREFS = "hidden_stations"
    private const val LIBRARY_PREFS = "radio_library"

    fun export(context: Context): JSONObject {
        val root = JSONObject()
            .put("schema", 2)
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

        val custom = context.getSharedPreferences(CUSTOM_PREFS, Context.MODE_PRIVATE)
        root.put("customStations", custom.getString("items", "[]") ?: "[]")

        val hidden = context.getSharedPreferences(HIDDEN_PREFS, Context.MODE_PRIVATE)
        val hiddenArray = JSONArray()
        hidden.getStringSet("ids", emptySet()).orEmpty().sorted().forEach(hiddenArray::put)
        root.put("hiddenStations", hiddenArray)

        val library = context.getSharedPreferences(LIBRARY_PREFS, Context.MODE_PRIVATE)
        val libraryJson = JSONObject()
        library.all.forEach { (key, value) ->
            when (value) {
                is String -> libraryJson.put(key, value)
                is Set<*> -> {
                    val array = JSONArray()
                    value.filterIsInstance<String>().sorted().forEach(array::put)
                    libraryJson.put(key, array)
                }
                is Boolean, is Int, is Long, is Float -> libraryJson.put(key, value)
            }
        }
        root.put("library", libraryJson)

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

        val customPrefs = context.getSharedPreferences(CUSTOM_PREFS, Context.MODE_PRIVATE)
        val customRaw = root.optString("customStations", "[]")
        customPrefs.edit().putString("items", customRaw).apply()

        val hiddenPrefs = context.getSharedPreferences(HIDDEN_PREFS, Context.MODE_PRIVATE)
        val hiddenSet = buildSet {
            val array = root.optJSONArray("hiddenStations") ?: JSONArray()
            for (i in 0 until array.length()) {
                array.optString(i).takeIf { it.isNotBlank() }?.let(::add)
            }
        }
        hiddenPrefs.edit().putStringSet("ids", hiddenSet).apply()

        val library = context.getSharedPreferences(LIBRARY_PREFS, Context.MODE_PRIVATE)
        val libraryEditor = library.edit().clear()
        val libraryJson = root.optJSONObject("library")
        if (libraryJson != null) {
            val libraryKeys = libraryJson.keys()
            while (libraryKeys.hasNext()) {
                val key = libraryKeys.next()
                when (val value = libraryJson.opt(key)) {
                    is String -> libraryEditor.putString(key, value)
                    is JSONArray -> {
                        val set = buildSet {
                            for (i in 0 until value.length()) {
                                value.optString(i).takeIf { it.isNotBlank() }?.let(::add)
                            }
                        }
                        libraryEditor.putStringSet(key, set)
                    }
                    is Boolean -> libraryEditor.putBoolean(key, value)
                    is Int -> libraryEditor.putInt(key, value)
                    is Long -> libraryEditor.putLong(key, value)
                    is Number -> libraryEditor.putFloat(key, value.toFloat())
                }
            }
        } else {
            val favorites = buildSet {
                val array = root.optJSONArray("favorites") ?: JSONArray()
                for (i in 0 until array.length()) {
                    array.optString(i).takeIf { it.isNotBlank() }?.let(::add)
                }
            }
            libraryEditor.putStringSet("favorites", favorites)
            libraryEditor.putString("recent", root.optString("recent"))
        }
        libraryEditor.apply()

        SyncClock.set(context, root.optLong("updatedAt", System.currentTimeMillis()))
        StationRepository.get(context).reloadOverrides()
    }
}
