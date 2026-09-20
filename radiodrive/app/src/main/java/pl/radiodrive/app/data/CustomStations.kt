package pl.radiodrive.app.data

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import pl.radiodrive.app.model.Station
import pl.radiodrive.app.sync.SyncClock

class CustomStations(private val context: Context) {
    private val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    fun all(): List<Station> = runCatching {
        val array = JSONArray(prefs.getString(KEY_ITEMS, "[]") ?: "[]")
        buildList {
            for (i in 0 until array.length()) {
                val o = array.optJSONObject(i) ?: continue
                val id = o.optString("id")
                val name = o.optString("name")
                val stream = o.optString("streamUrl")
                if (id.isBlank() || name.isBlank() || stream.isBlank()) continue
                add(
                    Station(
                        id = id,
                        name = name,
                        streamUrl = stream,
                        logoUrl = o.optString("logoUrl").takeIf { it.isNotBlank() },
                        homepage = o.optString("homepage").takeIf { it.isNotBlank() },
                        category = o.optString("category", "Własne"),
                        state = o.optString("state"),
                        tags = listOf("własne"),
                        codec = o.optString("codec"),
                        bitrate = o.optInt("bitrate", 0),
                        hls = o.optBoolean("hls", false),
                        votes = 0,
                        lastCheckOk = true,
                    )
                )
            }
        }
    }.getOrDefault(emptyList())

    fun save(station: Station) {
        val items = all().toMutableList()
        val index = items.indexOfFirst { it.id == station.id }
        if (index >= 0) items[index] = station else items.add(0, station)
        persist(items)
        SyncClock.touch(context)
    }

    fun delete(id: String) {
        persist(all().filterNot { it.id == id })
        SyncClock.touch(context)
    }

    fun isCustom(id: String): Boolean = id.startsWith("custom-") || all().any { it.id == id }

    private fun persist(items: List<Station>) {
        val array = JSONArray()
        items.forEach { s ->
            array.put(
                JSONObject()
                    .put("id", s.id)
                    .put("name", s.name)
                    .put("streamUrl", s.streamUrl)
                    .put("logoUrl", s.logoUrl.orEmpty())
                    .put("homepage", s.homepage.orEmpty())
                    .put("category", s.category)
                    .put("state", s.state)
                    .put("codec", s.codec)
                    .put("bitrate", s.bitrate)
                    .put("hls", s.hls)
            )
        }
        prefs.edit().putString(KEY_ITEMS, array.toString()).apply()
    }

    companion object {
        const val PREFS = "custom_stations"
        private const val KEY_ITEMS = "items"
    }
}
