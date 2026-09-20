package pl.radiodrive.app.data

import android.content.Context
import pl.radiodrive.app.model.Station
import org.json.JSONArray

class StationRepository(private val context: Context) {
    private val stations: List<Station> by lazy { loadStations() }

    fun all(): List<Station> = stations
    fun find(id: String): Station? = stations.firstOrNull { it.id == id }
    fun categories(): List<String> = stations.map { it.category }.distinct().sorted()
    fun inCategory(category: String): List<Station> = stations.filter { it.category == category }
    fun search(query: String): List<Station> {
        val q = query.trim().lowercase()
        if (q.isBlank()) return emptyList()
        return stations.filter {
            it.name.lowercase().contains(q) ||
                it.subtitle.lowercase().contains(q) ||
                it.category.lowercase().contains(q)
        }
    }

    private fun loadStations(): List<Station> {
        val raw = context.assets.open("stations.json").bufferedReader().use { it.readText() }
        val array = JSONArray(raw)
        return buildList {
            for (i in 0 until array.length()) {
                val o = array.getJSONObject(i)
                add(
                    Station(
                        id = o.getString("id"),
                        name = o.getString("name"),
                        subtitle = o.optString("subtitle"),
                        streamUrl = o.getString("streamUrl"),
                        category = o.optString("category", "Inne"),
                        logoUrl = if (o.isNull("logoUrl")) null else o.optString("logoUrl").takeIf { it.isNotBlank() },
                    )
                )
            }
        }
    }
}
