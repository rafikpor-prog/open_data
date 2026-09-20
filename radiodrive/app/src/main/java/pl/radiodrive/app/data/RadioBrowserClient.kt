package pl.radiodrive.app.data

import org.json.JSONArray
import pl.radiodrive.app.model.Station
import java.io.BufferedReader
import java.net.HttpURLConnection
import java.net.URL
import java.util.Locale

class RadioBrowserClient {

    private val fallbackServers = listOf(
        "https://de1.api.radio-browser.info",
        "https://nl1.api.radio-browser.info",
    )

    fun fetchPolishStationsRaw(): String {
        val servers = discoverServers().ifEmpty { fallbackServers }.shuffled()
        var lastError: Throwable? = null
        for (base in servers) {
            try {
                return get(
                    "$base/json/stations/bycountrycodeexact/PL" +
                        "?hidebroken=true&order=votes&reverse=true&limit=5000"
                )
            } catch (t: Throwable) {
                lastError = t
            }
        }
        throw lastError ?: IllegalStateException("Brak dostępnego serwera katalogu")
    }

    fun parseStations(raw: String): List<Station> {
        val array = JSONArray(raw)
        val result = ArrayList<Station>(array.length())
        val seen = HashSet<String>()
        for (i in 0 until array.length()) {
            val o = array.optJSONObject(i) ?: continue
            val id = o.optString("stationuuid").trim()
            val name = o.optString("name").trim()
            val stream = o.optString("url_resolved").trim()
                .ifBlank { o.optString("url").trim() }
            val country = o.optString("countrycode").trim().uppercase(Locale.ROOT)
            val lastOk = when (val v = o.opt("lastcheckok")) {
                is Boolean -> v
                is Number -> v.toInt() == 1
                else -> v?.toString() == "1" || v?.toString().equals("true", true)
            }
            if (id.isBlank() || name.isBlank() || stream.isBlank()) continue
            if (country.isNotBlank() && country != "PL") continue
            if (!lastOk || !seen.add(id)) continue

            val tagList = o.optString("tags")
                .split(',')
                .map { it.trim() }
                .filter { it.isNotBlank() }
                .distinct()
                .take(12)

            result += Station(
                id = id,
                name = name,
                streamUrl = stream,
                logoUrl = o.optString("favicon").trim().takeIf { it.startsWith("http") },
                homepage = o.optString("homepage").trim().takeIf { it.startsWith("http") },
                category = classify(tagList, name),
                state = o.optString("state").trim(),
                tags = tagList,
                codec = o.optString("codec").trim().uppercase(Locale.ROOT),
                bitrate = o.optInt("bitrate", 0).coerceAtLeast(0),
                hls = o.optInt("hls", 0) == 1 || o.optBoolean("hls", false),
                votes = o.optInt("votes", 0).coerceAtLeast(0),
                lastCheckOk = lastOk,
                lastCheckTime = o.optString("lastcheckoktime_iso8601").trim(),
            )
        }

        return result.sortedWith(
            compareByDescending<Station> { it.votes }
                .thenBy(String.CASE_INSENSITIVE_ORDER) { it.name }
        )
    }

    fun registerClick(stationId: String) {
        for (base in fallbackServers.shuffled()) {
            runCatching {
                get("$base/json/url/$stationId")
                return
            }
        }
    }

    private fun discoverServers(): List<String> = runCatching {
        val raw = get("https://all.api.radio-browser.info/json/servers")
        val a = JSONArray(raw)
        buildList {
            for (i in 0 until a.length()) {
                val name = a.optJSONObject(i)?.optString("name")?.trim().orEmpty()
                if (name.isNotBlank()) add("https://$name")
            }
        }.distinct()
    }.getOrDefault(emptyList())

    private fun get(url: String): String {
        val connection = (URL(url).openConnection() as HttpURLConnection).apply {
            requestMethod = "GET"
            connectTimeout = 12_000
            readTimeout = 25_000
            setRequestProperty("User-Agent", "RadioDrive/2.0 (Android)")
            setRequestProperty("Accept", "application/json")
            instanceFollowRedirects = true
        }
        try {
            val code = connection.responseCode
            if (code !in 200..299) error("HTTP $code")
            return connection.inputStream.bufferedReader(Charsets.UTF_8)
                .use(BufferedReader::readText)
        } finally {
            connection.disconnect()
        }
    }

    private fun classify(tags: List<String>, name: String): String {
        val text = (tags.joinToString(" ") + " " + name).lowercase(Locale.ROOT)
        return when {
            listOf("news", "wiadomo", "informac", "talk", "public").any(text::contains) -> "Informacje"
            listOf("rock", "metal", "alternative", "alternatyw").any(text::contains) -> "Rock"
            listOf("dance", "club", "house", "techno", "electro").any(text::contains) -> "Dance"
            listOf("jazz", "blues", "soul").any(text::contains) -> "Jazz / Soul"
            listOf("classic", "klasycz", "chopin").any(text::contains) -> "Klasyczna"
            listOf("hip hop", "rap", "urban").any(text::contains) -> "Hip-hop"
            listOf("disco", "polo").any(text::contains) -> "Disco"
            listOf("relig", "christ", "katol").any(text::contains) -> "Religijne"
            listOf("local", "regional", "lokal").any(text::contains) -> "Regionalne"
            listOf("pop", "hits", "music", "muzyka").any(text::contains) -> "Muzyka"
            else -> "Różne"
        }
    }
}
