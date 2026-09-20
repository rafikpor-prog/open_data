package pl.radiodrive.app.data

import android.content.Context
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import pl.radiodrive.app.model.Station
import java.io.File

data class CatalogState(
    val stations: List<Station> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null,
    val source: String = "cache",
)

class StationRepository private constructor(private val context: Context) {
    private val client = RadioBrowserClient()
    private val overrides = StationOverrides(context)
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val cacheFile = File(context.filesDir, "radiodrive_stations_pl.json")

    private var baseStations: List<Station> = loadCached().ifEmpty { loadFallback() }
    private val _state = MutableStateFlow(CatalogState(stations = overrides.apply(baseStations)))
    val state: StateFlow<CatalogState> = _state.asStateFlow()

    init { refresh() }

    fun all(): List<Station> = _state.value.stations

    fun find(id: String): Station? = all().firstOrNull { it.id == id }

    fun baseStation(id: String): Station? = baseStations.firstOrNull { it.id == id }

    fun categories(): List<String> = all().map { it.category }.distinct().sorted()

    fun regions(): List<String> = all().map { it.state }.filter { it.isNotBlank() }.distinct().sorted()

    fun refresh() {
        if (_state.value.isLoading) return
        _state.update { it.copy(isLoading = true, error = null) }
        scope.launch {
            runCatching {
                val raw = client.fetchPolishStationsRaw()
                val parsed = client.parseStations(raw)
                require(parsed.isNotEmpty()) { "Katalog nie zwrócił aktywnych stacji" }
                cacheFile.writeText(raw, Charsets.UTF_8)
                parsed
            }.onSuccess { stations ->
                baseStations = stations
                _state.value = CatalogState(
                    stations = overrides.apply(stations),
                    isLoading = false,
                    error = null,
                    source = "Publiczne strumienie nadawców • Polska",
                )
            }.onFailure { error ->
                _state.update {
                    it.copy(
                        isLoading = false,
                        error = "Nie udało się odświeżyć katalogu: ${error.message ?: "błąd sieci"}",
                    )
                }
            }
        }
    }

    fun saveEditedStation(station: Station) {
        overrides.save(station)
        _state.update { state ->
            state.copy(stations = state.stations.map { if (it.id == station.id) station else it })
        }
    }

    fun resetEditedStation(stationId: String) {
        overrides.reset(stationId)
        val original = baseStation(stationId) ?: return
        _state.update { state ->
            state.copy(stations = state.stations.map { if (it.id == stationId) original else it })
        }
    }

    fun isEdited(stationId: String): Boolean = overrides.hasOverride(stationId)

    fun reloadOverrides() {
        _state.update { state ->
            state.copy(stations = overrides.apply(baseStations))
        }
    }

    fun trackClick(stationId: String) {
        scope.launch { runCatching { client.registerClick(stationId) } }
    }

    private fun loadCached(): List<Station> = runCatching {
        if (!cacheFile.exists()) emptyList()
        else client.parseStations(cacheFile.readText(Charsets.UTF_8))
    }.getOrDefault(emptyList())

    private fun loadFallback(): List<Station> = runCatching {
        val raw = context.assets.open("stations.json").bufferedReader().use { it.readText() }
        val legacy = org.json.JSONArray(raw)
        buildList {
            for (i in 0 until legacy.length()) {
                val o = legacy.getJSONObject(i)
                add(
                    Station(
                        id = o.getString("id"),
                        name = o.getString("name"),
                        streamUrl = o.getString("streamUrl"),
                        logoUrl = if (o.isNull("logoUrl")) null else o.optString("logoUrl").takeIf { it.isNotBlank() },
                        category = o.optString("category", "Różne"),
                        tags = listOf(o.optString("category", "Różne")),
                    )
                )
            }
        }
    }.getOrDefault(emptyList())

    companion object {
        @Volatile private var INSTANCE: StationRepository? = null

        fun get(context: Context): StationRepository =
            INSTANCE ?: synchronized(this) {
                INSTANCE ?: StationRepository(context.applicationContext).also { INSTANCE = it }
            }
    }
}
