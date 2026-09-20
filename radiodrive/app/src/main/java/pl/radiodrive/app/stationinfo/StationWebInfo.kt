package pl.radiodrive.app.stationinfo

import android.content.Intent
import android.net.Uri
import android.text.Html
import android.util.Xml
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Article
import androidx.compose.material.icons.rounded.CalendarMonth
import androidx.compose.material.icons.rounded.ChevronRight
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.xmlpull.v1.XmlPullParser
import pl.radiodrive.app.model.Station
import pl.radiodrive.app.ui.theme.RadioAmber
import java.net.HttpURLConnection
import java.net.URL
import java.util.Locale

data class StationNewsItem(val title: String, val url: String?)
data class StationWebInfo(
    val news: List<StationNewsItem> = emptyList(),
    val scheduleUrl: String? = null,
    val message: String? = null,
)

object StationWebInfoRepository {

    suspend fun load(station: Station): StationWebInfo = withContext(Dispatchers.IO) {
        val schedule = scheduleUrl(station)
        val homepage = station.homepage
        if (homepage.isNullOrBlank()) return@withContext StationWebInfo(scheduleUrl = schedule)

        val news = runCatching {
            val html = get(homepage)
            val feed = findFeedUrl(homepage, html) ?: return@runCatching emptyList()
            parseFeed(get(feed), feed).take(4)
        }.getOrDefault(emptyList())

        StationWebInfo(
            news = news,
            scheduleUrl = schedule,
            message = if (news.isEmpty() && schedule == null) "Ta stacja nie udostępniła RadioDrive publicznego źródła wiadomości ani ramówki." else null
        )
    }

    private fun scheduleUrl(station: Station): String? {
        val n = station.name.lowercase(Locale.ROOT)
        val home = station.homepage.orEmpty().lowercase(Locale.ROOT)
        return when {
            "polskie radio 24" in n || "pr24" in n -> "https://player.polskieradio.pl/schedule/pr24"
            "jedynka" in n || "program 1" in n || "polskieradio.pl" in home -> "https://stream1.polskieradio.pl/Portal/Schedule/Schedule.aspx"
            "eska" in n || "eska.pl" in home -> "https://www.eska.pl/co-bylo-grane/"
            "radio zet" in n || "radiozet.pl" in home -> "https://player.radiozet.pl/"
            "rmf" in n || "rmf.fm" in home -> "https://www.rmf.fm/radio/"
            else -> null
        }
    }

    private fun findFeedUrl(base: String, html: String): String? {
        val patterns = listOf(
            Regex("""(?is)<link[^>]*type\s*=\s*["']application/(?:rss\+xml|atom\+xml)["'][^>]*href\s*=\s*["']([^"']+)["']"""),
            Regex("""(?is)<link[^>]*href\s*=\s*["']([^"']+)["'][^>]*type\s*=\s*["']application/(?:rss\+xml|atom\+xml)["']""")
        )
        val href = patterns.firstNotNullOfOrNull { it.find(html)?.groupValues?.getOrNull(1) } ?: return null
        return runCatching { URL(URL(base), href).toString() }.getOrNull()
    }

    private fun parseFeed(xml: String, base: String): List<StationNewsItem> {
        val parser = Xml.newPullParser()
        parser.setInput(xml.reader())
        val result = mutableListOf<StationNewsItem>()
        var inItem = false
        var title: String? = null
        var link: String? = null

        while (parser.eventType != XmlPullParser.END_DOCUMENT && result.size < 6) {
            when (parser.eventType) {
                XmlPullParser.START_TAG -> when (parser.name.lowercase()) {
                    "item", "entry" -> { inItem = true; title = null; link = null }
                    "title" -> if (inItem) title = runCatching { parser.nextText() }.getOrNull()
                    "link" -> if (inItem) {
                        val href = parser.getAttributeValue(null, "href")
                        link = href ?: runCatching { parser.nextText() }.getOrNull()
                    }
                }
                XmlPullParser.END_TAG -> if ((parser.name.equals("item", true) || parser.name.equals("entry", true)) && inItem) {
                    val cleanTitle = title?.let(::cleanText)?.takeIf { it.isNotBlank() }
                    if (cleanTitle != null) {
                        val resolved = link?.let { runCatching { URL(URL(base), it).toString() }.getOrNull() }
                        result += StationNewsItem(cleanTitle, resolved)
                    }
                    inItem = false
                }
            }
            parser.next()
        }
        return result
    }

    @Suppress("DEPRECATION")
    private fun cleanText(text: String): String =
        Html.fromHtml(text, Html.FROM_HTML_MODE_LEGACY).toString().trim().replace(Regex("\\s+"), " ")

    private fun get(url: String): String {
        val connection = (URL(url).openConnection() as HttpURLConnection).apply {
            requestMethod = "GET"
            connectTimeout = 8_000
            readTimeout = 10_000
            instanceFollowRedirects = true
            setRequestProperty("User-Agent", "RadioDrive/2.2 Android")
            setRequestProperty("Accept", "text/html,application/rss+xml,application/atom+xml,application/xml,text/xml,*/*")
        }
        return try {
            if (connection.responseCode !in 200..299) error("HTTP ${connection.responseCode}")
            connection.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() }
        } finally {
            connection.disconnect()
        }
    }
}

@Composable
fun StationWebInfoPanel(station: Station) {
    val context = LocalContext.current
    var loading by remember(station.id) { mutableStateOf(true) }
    var info by remember(station.id) { mutableStateOf(StationWebInfo()) }

    LaunchedEffect(station.id, station.homepage) {
        loading = true
        info = StationWebInfoRepository.load(station)
        loading = false
    }

    Surface(shape = RoundedCornerShape(26.dp), color = MaterialTheme.colorScheme.surfaceVariant) {
        Column(Modifier.fillMaxWidth().padding(18.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Rounded.Article, null, tint = RadioAmber)
                Spacer(Modifier.width(10.dp))
                Column(Modifier.weight(1f)) {
                    Text("Informacje od nadawcy", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Black)
                    Text("Ramówka i wiadomości tylko z publicznych źródeł stacji", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                if (loading) CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp)
            }

            info.scheduleUrl?.let { url ->
                Spacer(Modifier.height(12.dp))
                OutlinedButton(onClick = { open(context, url) }) {
                    Icon(Icons.Rounded.CalendarMonth, null)
                    Spacer(Modifier.width(8.dp))
                    Text("Ramówka / co gramy")
                }
            }

            if (info.news.isNotEmpty()) {
                Spacer(Modifier.height(12.dp))
                Text("Najnowsze wiadomości", fontWeight = FontWeight.Bold)
                info.news.forEach { item ->
                    Row(
                        Modifier
                            .fillMaxWidth()
                            .clickable(enabled = item.url != null) { item.url?.let { open(context, it) } }
                            .padding(vertical = 9.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(item.title, Modifier.weight(1f), maxLines = 2, overflow = TextOverflow.Ellipsis)
                        if (item.url != null) Icon(Icons.Rounded.ChevronRight, null, tint = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    HorizontalDivider()
                }
            } else if (!loading) {
                info.message?.let {
                    Spacer(Modifier.height(10.dp))
                    Text(it, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
    }
}

private fun open(context: android.content.Context, url: String) {
    runCatching { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url))) }
}
