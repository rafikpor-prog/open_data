package pl.radiodrive.app.alerts

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.Geocoder
import android.location.Location
import android.location.LocationManager
import android.util.Xml
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.ReportProblem
import androidx.compose.material.icons.rounded.Refresh
import androidx.compose.material.icons.rounded.Traffic
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import org.json.JSONArray
import org.json.JSONObject
import org.xmlpull.v1.XmlPullParser
import pl.radiodrive.app.ui.theme.RadioAmber
import java.net.HttpURLConnection
import java.net.URL
import java.text.Normalizer
import java.util.Locale

enum class AlertSource { RCB, RSO, ROAD }

data class SafetyAlert(
    val id: String,
    val source: AlertSource,
    val title: String,
    val body: String,
    val region: String = "",
    val date: String = "",
    val distanceKm: Int? = null,
)

data class SafetyFeedState(
    val loading: Boolean = false,
    val alerts: List<SafetyAlert> = emptyList(),
    val error: String? = null,
    val updatedAt: Long = 0L,
)

class SafetyAlertsRepository private constructor(private val context: Context) {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val _state = MutableStateFlow(SafetyFeedState())
    val state = _state.asStateFlow()

    init {
        refresh()
        scope.launch {
            while (isActive) {
                delay(5 * 60 * 1000L)
                refresh()
            }
        }
    }

    fun refresh() {
        if (_state.value.loading) return
        _state.value = _state.value.copy(loading = true, error = null)
        scope.launch {
            val location = currentLocation()
            val regionSlug = currentVoivodeshipSlug(location)
            val result = runCatching {
                val rso = fetchRso(regionSlug)
                val roads = fetchRoads(location)
                (rso + roads)
                    .distinctBy { it.id }
                    .take(12)
            }
            result.onSuccess {
                _state.value = SafetyFeedState(
                    alerts = it,
                    loading = false,
                    updatedAt = System.currentTimeMillis(),
                )
            }.onFailure {
                _state.value = _state.value.copy(
                    loading = false,
                    error = it.message ?: "Nie udało się pobrać komunikatów bezpieczeństwa."
                )
            }
        }
    }

    private fun fetchRso(regionSlug: String?): List<SafetyAlert> {
        val region = regionSlug ?: "wszystkie"
        val jsonUrl = "https://komunikaty.tvp.pl/komunikatyxml/$region/wszystkie/0?_format=json"
        val raw = get(jsonUrl)
        val parsed = runCatching { parseRsoJson(raw) }.getOrDefault(emptyList())
        if (parsed.isNotEmpty()) return parsed

        val xmlUrl = "https://komunikaty.tvp.pl/komunikatyxml/$region/wszystkie/0?_format=xml"
        return parseRsoXml(get(xmlUrl))
    }

    private fun parseRsoJson(raw: String): List<SafetyAlert> {
        val root: Any = raw.trim().let {
            if (it.startsWith("[")) JSONArray(it) else JSONObject(it)
        }
        val objects = mutableListOf<JSONObject>()
        collectObjects(root, objects)

        return objects.mapNotNull { o ->
            val title = firstString(o, "tytul", "title", "naglowek", "headline", "subject", "nazwa")
            val body = firstString(o, "tresc", "opis", "description", "content", "text", "details", "komunikat")
            if (title.isBlank() || (body.isBlank() && o.length() < 3)) return@mapNotNull null

            val date = firstString(o, "data", "date", "created_at", "published_at", "data_publikacji", "publicationDate")
            val region = firstString(o, "wojewodztwo", "province", "region", "obszar")
            val category = firstString(o, "kategoria", "category", "typ", "type")
            val id = firstString(o, "id", "identifier", "uuid").ifBlank {
                "rso-${(title + body + date).hashCode()}"
            }
            val all = listOf(title, body, category).joinToString(" ").lowercase(Locale.ROOT)
            val source = if ("rcb" in all) AlertSource.RCB else AlertSource.RSO

            SafetyAlert(
                id = id,
                source = source,
                title = clean(title),
                body = clean(body).ifBlank { category },
                region = clean(region),
                date = clean(date),
            )
        }
    }

    private fun collectObjects(node: Any?, out: MutableList<JSONObject>) {
        when (node) {
            is JSONObject -> {
                out += node
                val keys = node.keys()
                while (keys.hasNext()) {
                    val key = keys.next()
                    collectObjects(node.opt(key), out)
                }
            }
            is JSONArray -> for (i in 0 until node.length()) collectObjects(node.opt(i), out)
        }
    }

    private fun parseRsoXml(raw: String): List<SafetyAlert> {
        val parser = Xml.newPullParser().apply { setInput(raw.reader()) }
        val result = mutableListOf<SafetyAlert>()
        var fields = linkedMapOf<String, String>()
        var itemDepth = -1

        while (parser.eventType != XmlPullParser.END_DOCUMENT) {
            if (parser.eventType == XmlPullParser.START_TAG) {
                val name = parser.name.lowercase(Locale.ROOT)
                if (name in setOf("komunikat", "item", "alert")) {
                    fields = linkedMapOf()
                    itemDepth = parser.depth
                } else if (itemDepth > 0 && parser.depth == itemDepth + 1) {
                    runCatching { parser.nextText() }.getOrNull()?.let { fields[name] = it }
                }
            } else if (parser.eventType == XmlPullParser.END_TAG && parser.depth == itemDepth) {
                val title = fields["tytul"] ?: fields["title"] ?: fields["nazwa"] ?: ""
                val body = fields["tresc"] ?: fields["opis"] ?: fields["description"] ?: ""
                if (title.isNotBlank()) {
                    val all = (title + " " + body + " " + (fields["kategoria"] ?: "")).lowercase(Locale.ROOT)
                    result += SafetyAlert(
                        id = fields["id"] ?: "rso-${(title + body).hashCode()}",
                        source = if ("rcb" in all) AlertSource.RCB else AlertSource.RSO,
                        title = clean(title),
                        body = clean(body),
                        region = clean(fields["wojewodztwo"].orEmpty()),
                        date = clean(fields["data"].orEmpty()),
                    )
                }
                itemDepth = -1
            }
            parser.next()
        }
        return result
    }

    private fun fetchRoads(location: Location?): List<SafetyAlert> {
        val raw = runCatching {
            get("https://www.gddkia.gov.pl/dane/zima_html/utrdane.xml")
        }.recoverCatching {
            get("http://www.gddkia.gov.pl/dane/zima_html/utrdane.xml")
        }.getOrThrow()

        val parser = Xml.newPullParser().apply { setInput(raw.reader()) }
        val result = mutableListOf<SafetyAlert>()
        var fields = linkedMapOf<String, String>()
        var inItem = false

        while (parser.eventType != XmlPullParser.END_DOCUMENT) {
            when (parser.eventType) {
                XmlPullParser.START_TAG -> {
                    val name = parser.name.lowercase(Locale.ROOT)
                    if (name == "utr") {
                        fields = linkedMapOf()
                        inItem = true
                    } else if (inItem && name in ROAD_TAGS) {
                        runCatching { parser.nextText() }.getOrNull()?.let { fields[name] = it }
                    }
                }
                XmlPullParser.END_TAG -> if (parser.name.equals("utr", true) && inItem) {
                    roadAlert(fields, location)?.let(result::add)
                    inItem = false
                }
            }
            parser.next()
        }

        return result.sortedWith(
            compareBy<SafetyAlert> { it.distanceKm ?: Int.MAX_VALUE }
                .thenBy { it.title }
        ).take(8)
    }

    private fun roadAlert(fields: Map<String, String>, location: Location?): SafetyAlert? {
        val road = fields["nr_drogi"].orEmpty()
        val section = fields["nazwa_odcinka"].orEmpty()
        if (road.isBlank() && section.isBlank()) return null

        val lat = fields["geo_lat"]?.toDoubleOrNull()
        val lon = fields["geo_long"]?.toDoubleOrNull()
        val distanceKm = if (location != null && lat != null && lon != null) {
            val out = FloatArray(1)
            Location.distanceBetween(location.latitude, location.longitude, lat, lon, out)
            (out[0] / 1000f).toInt()
        } else null

        if (distanceKm != null && distanceKm > 180) return null

        val type = when (fields["typ"]) {
            "W" -> "Wypadek"
            "K" -> "Katastrofa"
            "I" -> "Zdarzenie"
            else -> "Utrudnienie"
        }
        val details = buildList {
            if (fields["droga_zamknieta"].equals("true", true)) add("droga zamknięta")
            if (fields["ruch_wahadlowy"].equals("true", true)) add("ruch wahadłowy")
            fields["ogr_predkosc"]?.takeIf { it.isNotBlank() && it != "0" }?.let { add("ograniczenie do $it km/h") }
            fields["objazd"]?.takeIf { it.isNotBlank() }?.let { add("objazd: $it") }
        }.joinToString(" • ")

        return SafetyAlert(
            id = "road-${(road + section + fields["km"]).hashCode()}",
            source = AlertSource.ROAD,
            title = "$type • $road ${section}".trim(),
            body = details.ifBlank { fields["woj"].orEmpty() },
            region = fields["woj"].orEmpty(),
            date = fields["data_powstania"].orEmpty(),
            distanceKm = distanceKm,
        )
    }

    private fun currentLocation(): Location? {
        if (ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION) != PackageManager.PERMISSION_GRANTED) return null
        val manager = context.getSystemService(Context.LOCATION_SERVICE) as LocationManager
        return manager.getProviders(true)
            .mapNotNull { runCatching { manager.getLastKnownLocation(it) }.getOrNull() }
            .maxByOrNull { it.time }
    }

    @Suppress("DEPRECATION")
    private fun currentVoivodeshipSlug(location: Location?): String? {
        location ?: return null
        return runCatching {
            val area = Geocoder(context, Locale("pl", "PL"))
                .getFromLocation(location.latitude, location.longitude, 1)
                ?.firstOrNull()
                ?.adminArea
                ?: return@runCatching null
            slug(area)
        }.getOrNull()
    }

    private fun slug(value: String): String {
        val normalized = Normalizer.normalize(value.lowercase(Locale.ROOT), Normalizer.Form.NFD)
            .replace(Regex("\\p{Mn}+"), "")
            .replace("wojewodztwo", "")
            .replace("woj.", "")
            .trim()
            .replace(Regex("[^a-z]+"), "-")
            .trim('-')
        return normalized.takeIf { it.isNotBlank() } ?: "wszystkie"
    }

    private fun firstString(o: JSONObject, vararg keys: String): String =
        keys.firstNotNullOfOrNull { key ->
            o.opt(key)?.let { value ->
                when (value) {
                    is String -> value
                    is Number, is Boolean -> value.toString()
                    is JSONObject -> firstString(value, "name", "title", "nazwa", "value")
                    else -> null
                }
            }?.takeIf { it.isNotBlank() }
        }.orEmpty()

    private fun clean(value: String): String =
        value.replace(Regex("<[^>]+>"), " ")
            .replace(Regex("\\s+"), " ")
            .trim()
            .take(500)

    private fun get(url: String): String {
        val connection = (URL(url).openConnection() as HttpURLConnection).apply {
            requestMethod = "GET"
            connectTimeout = 10_000
            readTimeout = 15_000
            instanceFollowRedirects = true
            setRequestProperty("User-Agent", "RadioDrive/2.4 Android")
            setRequestProperty("Accept", "application/json,application/xml,text/xml,*/*")
        }
        return try {
            if (connection.responseCode !in 200..299) error("HTTP ${connection.responseCode}")
            connection.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() }
        } finally {
            connection.disconnect()
        }
    }

    companion object {
        private val ROAD_TAGS = setOf(
            "typ", "nr_drogi", "woj", "km", "dl", "geo_lat", "geo_long",
            "nazwa_odcinka", "data_powstania", "data_likwidacji", "objazd",
            "ogr_predkosc", "ruch_wahadlowy", "droga_zamknieta"
        )

        @Volatile private var INSTANCE: SafetyAlertsRepository? = null

        fun get(context: Context): SafetyAlertsRepository =
            INSTANCE ?: synchronized(this) {
                INSTANCE ?: SafetyAlertsRepository(context.applicationContext).also { INSTANCE = it }
            }
    }
}

@Composable
fun SafetyAlertsPanel() {
    val context = androidx.compose.ui.platform.LocalContext.current
    val repository = remember { SafetyAlertsRepository.get(context.applicationContext) }
    val state by repository.state.collectAsStateWithLifecycle()

    Surface(shape = RoundedCornerShape(26.dp), color = MaterialTheme.colorScheme.surfaceVariant) {
        Column(Modifier.fillMaxWidth().padding(18.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Surface(shape = CircleShape, color = MaterialTheme.colorScheme.error.copy(alpha = .12f)) {
                    Icon(
                        Icons.Rounded.ReportProblem,
                        contentDescription = null,
                        modifier = Modifier.padding(10.dp),
                        tint = MaterialTheme.colorScheme.error
                    )
                }
                Spacer(Modifier.width(10.dp))
                Column(Modifier.weight(1f)) {
                    Text("Bezpieczeństwo i droga", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Black)
                    Text("RSO / Alert RCB / GDDKiA", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                IconButton(onClick = repository::refresh, enabled = !state.loading) {
                    if (state.loading) CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp)
                    else Icon(Icons.Rounded.Refresh, "Odśwież komunikaty")
                }
            }

            Spacer(Modifier.height(10.dp))

            if (state.alerts.isEmpty() && !state.loading) {
                Text(
                    state.error ?: "Brak aktywnych komunikatów pasujących do bieżącej lokalizacji.",
                    style = MaterialTheme.typography.bodyMedium
                )
            } else {
                state.alerts.take(6).forEachIndexed { index, alert ->
                    AlertRow(alert)
                    if (index < state.alerts.take(6).lastIndex) HorizontalDivider(Modifier.padding(vertical = 6.dp))
                }
            }

            state.error?.takeIf { state.alerts.isNotEmpty() }?.let {
                Spacer(Modifier.height(8.dp))
                Text(it, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.error)
            }
        }
    }
}

@Composable
private fun AlertRow(alert: SafetyAlert) {
    val accent = when (alert.source) {
        AlertSource.RCB -> MaterialTheme.colorScheme.error
        AlertSource.RSO -> RadioAmber
        AlertSource.ROAD -> MaterialTheme.colorScheme.tertiary
    }
    Row(Modifier.fillMaxWidth().padding(vertical = 4.dp), verticalAlignment = Alignment.Top) {
        Icon(
            if (alert.source == AlertSource.ROAD) Icons.Rounded.Traffic else Icons.Rounded.ReportProblem,
            contentDescription = null,
            tint = accent,
            modifier = Modifier.size(20.dp)
        )
        Spacer(Modifier.width(10.dp))
        Column(Modifier.weight(1f)) {
            Text(
                when (alert.source) {
                    AlertSource.RCB -> "ALERT RCB"
                    AlertSource.RSO -> "RSO"
                    AlertSource.ROAD -> "DROGA"
                },
                style = MaterialTheme.typography.labelSmall,
                fontWeight = FontWeight.Black,
                color = accent
            )
            Text(alert.title, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.bodyMedium)
            if (alert.body.isNotBlank()) {
                Text(alert.body, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            val meta = buildList {
                alert.distanceKm?.let { add("$it km") }
                if (alert.region.isNotBlank()) add(alert.region)
                if (alert.date.isNotBlank()) add(alert.date)
            }.joinToString(" • ")
            if (meta.isNotBlank()) Text(meta, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}
