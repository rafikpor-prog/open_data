package pl.radiodrive.app.data

import android.content.Context
import org.json.JSONObject
import pl.radiodrive.app.model.Station
import pl.radiodrive.app.sync.SyncClock

class StationOverrides(private val context: Context) {
    private val prefs = context.getSharedPreferences("station_overrides", Context.MODE_PRIVATE)

    fun apply(stations: List<Station>): List<Station> = stations.map(::apply)

    fun apply(station: Station): Station {
        val raw = prefs.getString(station.id, null) ?: return station
        return runCatching {
            val o = JSONObject(raw)
            station.copy(
                name = o.optString("name", station.name),
                streamUrl = o.optString("streamUrl", station.streamUrl),
                logoUrl = o.optString("logoUrl").takeIf { it.isNotBlank() } ?: station.logoUrl,
                homepage = o.optString("homepage").takeIf { it.isNotBlank() } ?: station.homepage,
                category = o.optString("category", station.category),
                state = o.optString("state", station.state),
            )
        }.getOrDefault(station)
    }

    fun save(station: Station) {
        val o = JSONObject()
            .put("name", station.name.trim())
            .put("streamUrl", station.streamUrl.trim())
            .put("logoUrl", station.logoUrl.orEmpty().trim())
            .put("homepage", station.homepage.orEmpty().trim())
            .put("category", station.category.trim())
            .put("state", station.state.trim())
            .put("updatedAt", System.currentTimeMillis())
        prefs.edit().putString(station.id, o.toString()).apply()
        SyncClock.touch(context)
    }

    fun reset(stationId: String) {
        prefs.edit().remove(stationId).apply()
        SyncClock.touch(context)
    }

    fun hasOverride(stationId: String): Boolean = prefs.contains(stationId)
}
