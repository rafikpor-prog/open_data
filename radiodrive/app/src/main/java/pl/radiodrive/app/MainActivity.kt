package pl.radiodrive.app

import android.content.ComponentName
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items as gridItems
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.blur
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.media3.common.MediaItem
import androidx.media3.common.MediaMetadata
import androidx.media3.common.Player
import androidx.media3.session.MediaController
import androidx.media3.session.SessionToken
import coil3.compose.AsyncImage
import com.google.common.util.concurrent.ListenableFuture
import pl.radiodrive.app.data.AppMigration
import pl.radiodrive.app.backup.LocalBackupPanel
import pl.radiodrive.app.data.StationRepository
import pl.radiodrive.app.data.UserLibrary
import pl.radiodrive.app.alerts.SafetyAlertsPanel
import pl.radiodrive.app.weather.WeatherPanel
import pl.radiodrive.app.weather.CompactWeatherInline
import pl.radiodrive.app.model.Station
import pl.radiodrive.app.playback.RadioPlaybackService
import pl.radiodrive.app.road.RoadAssistPanel
import pl.radiodrive.app.stationinfo.StationWebInfoPanel
import pl.radiodrive.app.ui.theme.RadioAmber
import pl.radiodrive.app.ui.theme.RadioCyan
import pl.radiodrive.app.ui.theme.RadioDriveTheme
import pl.radiodrive.app.ui.theme.RadioSurface2

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        AppMigration.run(applicationContext)
        enableEdgeToEdge()
        setContent {
            RadioDriveTheme {
                RadioDriveApp(rememberMediaController())
            }
        }
    }

    @Composable
    private fun rememberMediaController(): MediaController? {
        var controller by remember { mutableStateOf<MediaController?>(null) }
        val app = applicationContext
        DisposableEffect(Unit) {
            val token = SessionToken(app, ComponentName(app, RadioPlaybackService::class.java))
            val future: ListenableFuture<MediaController> = MediaController.Builder(app, token).buildAsync()
            future.addListener(
                { runCatching { future.get() }.onSuccess { controller = it } },
                ContextCompat.getMainExecutor(app)
            )
            onDispose {
                controller?.let(MediaController::release)
                if (!future.isDone) future.cancel(true)
            }
        }
        return controller
    }
}

private enum class AppTab { HOME, ALL, FAVORITES, WEATHER, MORE }

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun RadioDriveApp(controller: MediaController?) {
    val context = LocalContext.current
    val repository = remember { StationRepository.get(context.applicationContext) }
    val library = remember { UserLibrary(context.applicationContext) }
    val catalog by repository.state.collectAsStateWithLifecycle()

    var tab by rememberSaveable { mutableStateOf(AppTab.HOME) }
    var detailsId by rememberSaveable { mutableStateOf<String?>(null) }
    var currentId by remember { mutableStateOf(controller?.currentMediaItem?.mediaId) }
    var isPlaying by remember { mutableStateOf(controller?.isPlaying == true) }
    var isBuffering by remember { mutableStateOf(controller?.playbackState == Player.STATE_BUFFERING) }
    var liveTitle by remember { mutableStateOf<String?>(null) }
    var liveArtist by remember { mutableStateOf<String?>(null) }
    var streamMetadata by remember { mutableStateOf<List<String>>(emptyList()) }
    var favoriteVersion by remember { mutableIntStateOf(0) }
    var historyVersion by remember { mutableIntStateOf(0) }
    var restoredVersion by remember { mutableIntStateOf(0) }
    var editingStation by remember { mutableStateOf<Station?>(null) }
    var addingCustomStation by rememberSaveable { mutableStateOf(false) }

    DisposableEffect(controller) {
        if (controller == null) return@DisposableEffect onDispose { }
        val listener = object : Player.Listener {
            override fun onIsPlayingChanged(value: Boolean) { isPlaying = value }
            override fun onPlaybackStateChanged(playbackState: Int) {
                isBuffering = playbackState == Player.STATE_BUFFERING
            }
            override fun onMediaItemTransition(mediaItem: MediaItem?, reason: Int) {
                currentId = mediaItem?.mediaId
                liveTitle = null
                liveArtist = null
                streamMetadata = emptyList()
            }
            override fun onMediaMetadataChanged(mediaMetadata: MediaMetadata) {
                val id = controller.currentMediaItem?.mediaId.orEmpty()
                val station = repository.find(id)
                val title = mediaMetadata.title?.toString()?.trim().orEmpty()
                val artist = mediaMetadata.artist?.toString()?.trim().orEmpty()
                val usefulTitle = title.takeIf {
                    it.isNotBlank() && !it.equals(station?.name, ignoreCase = true)
                }
                if (usefulTitle != null) {
                    liveTitle = usefulTitle
                    liveArtist = artist.takeIf {
                        it.isNotBlank() && !it.equals(station?.category, ignoreCase = true)
                    }
                    val historyText = listOfNotNull(liveArtist, liveTitle).joinToString(" — ")
                    library.rememberTrack(id, historyText)
                    historyVersion++
                }
            }
            override fun onMetadata(metadata: androidx.media3.common.Metadata) {
                val decoded = buildList {
                    for (index in 0 until metadata.length()) {
                        prettifyStreamMetadata(metadata[index].toString())?.let(::add)
                    }
                }.distinct().take(8)
                if (decoded.isNotEmpty()) streamMetadata = decoded
            }
        }
        controller.addListener(listener)
        currentId = controller.currentMediaItem?.mediaId
        isPlaying = controller.isPlaying
        isBuffering = controller.playbackState == Player.STATE_BUFFERING
        onDispose { controller.removeListener(listener) }
    }

    val favorites = remember(favoriteVersion, restoredVersion) { library.favorites() }
    val current = catalog.stations.firstOrNull { it.id == currentId }
    val details = catalog.stations.firstOrNull { it.id == detailsId }
    val hiddenCount = repository.hiddenCount()

    Scaffold(
        topBar = {
            TopAppBar(
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Color(0xFF07111C),
                    titleContentColor = Color.White,
                    actionIconContentColor = RadioCyan,
                    navigationIconContentColor = Color.White
                ),
                title = {
                    if (details != null) {
                        Column {
                            Text(details.name, maxLines = 1, overflow = TextOverflow.Ellipsis, fontWeight = FontWeight.Black)
                            Text("RADIO • LIVE • POLSKA", style = MaterialTheme.typography.labelSmall, color = RadioCyan)
                        }
                    } else {
                        Column {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Text("Radio", fontWeight = FontWeight.Black)
                                Text("Drive", fontWeight = FontWeight.Black, color = RadioCyan)
                                Spacer(Modifier.width(7.dp))
                                Surface(shape = CircleShape, color = RadioCyan.copy(alpha = .14f)) {
                                    Text(
                                        "2.9",
                                        modifier = Modifier.padding(horizontal = 7.dp, vertical = 2.dp),
                                        style = MaterialTheme.typography.labelSmall,
                                        color = RadioCyan,
                                        fontWeight = FontWeight.Black
                                    )
                                }
                            }
                            Text(
                                "${catalog.stations.size} stacji • muzyka na każdą trasę",
                                style = MaterialTheme.typography.labelSmall,
                                color = Color.White.copy(alpha = .62f)
                            )
                        }
                    }
                },
                navigationIcon = {
                    if (details != null) {
                        IconButton(onClick = { detailsId = null }) { Icon(Icons.Rounded.ArrowBack, "Wróć") }
                    }
                },
                actions = {
                    if (details != null) {
                        IconButton(onClick = { editingStation = details }) {
                            Icon(Icons.Rounded.Edit, "Edytuj stację")
                        }
                    } else {
                        IconButton(onClick = { addingCustomStation = true }) {
                            Icon(Icons.Rounded.AddCircle, "Dodaj własną stację")
                        }
                        IconButton(onClick = repository::refresh) {
                            if (catalog.isLoading) CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp)
                            else Icon(Icons.Rounded.Refresh, "Odśwież")
                        }
                    }
                }
            )
        },
        bottomBar = {
            if (details == null) {
                Column {
                    current?.let { playing ->
                        StickyMiniPlayer(
                            station = playing,
                            isPlaying = isPlaying,
                            isBuffering = isBuffering,
                            liveTitle = liveTitle,
                            favorite = playing.id in favorites,
                            onOpen = { detailsId = playing.id },
                            onPrevious = {
                                adjacentStation(catalog.stations, playing.id, -1)?.let {
                                    play(controller, repository, it)
                                }
                            },
                            onPlayPause = {
                                if (controller?.isPlaying == true) controller.pause() else controller?.play()
                            },
                            onStop = { controller?.stop() },
                            onNext = {
                                adjacentStation(catalog.stations, playing.id, 1)?.let {
                                    play(controller, repository, it)
                                }
                            },
                            onFavorite = {
                                library.toggleFavorite(playing.id)
                                favoriteVersion++
                            }
                        )
                    }
                    NavigationBar(
                        containerColor = Color(0xFF08131F),
                        tonalElevation = 10.dp
                    ) {
                        NavigationBarItem(
                            selected = tab == AppTab.HOME,
                            onClick = { tab = AppTab.HOME },
                            icon = { Icon(Icons.Rounded.Radio, null) },
                            label = { Text("Radio") },
                            colors = neonNavigationColors()
                        )
                        NavigationBarItem(
                            selected = tab == AppTab.ALL,
                            onClick = { tab = AppTab.ALL },
                            icon = { Icon(Icons.Rounded.Search, null) },
                            label = { Text("Odkrywaj") },
                            colors = neonNavigationColors()
                        )
                        NavigationBarItem(
                            selected = tab == AppTab.FAVORITES,
                            onClick = { tab = AppTab.FAVORITES },
                            icon = {
                                Icon(
                                    if (tab == AppTab.FAVORITES) Icons.Rounded.Favorite else Icons.Rounded.FavoriteBorder,
                                    "Ulubione stacje"
                                )
                            },
                            label = { Text("Ulubione") },
                            colors = neonNavigationColors()
                        )
                        NavigationBarItem(
                            selected = tab == AppTab.WEATHER,
                            onClick = { tab = AppTab.WEATHER },
                            icon = { Icon(Icons.Rounded.Cloud, null) },
                            label = { Text("Pogoda") },
                            colors = neonNavigationColors()
                        )
                        NavigationBarItem(
                            selected = tab == AppTab.MORE,
                            onClick = { tab = AppTab.MORE },
                            icon = { Icon(Icons.Rounded.MoreHoriz, null) },
                            label = { Text("Więcej") },
                            colors = neonNavigationColors()
                        )
                    }
                }
            }
        }
    ) { padding ->
        if (details != null) {
            PlayerDetailsScreen(
                modifier = Modifier.padding(padding),
                station = details,
                isCurrent = details.id == currentId,
                isPlaying = isPlaying,
                isBuffering = isBuffering,
                liveTitle = if (details.id == currentId) liveTitle else null,
                liveArtist = if (details.id == currentId) liveArtist else null,
                history = remember(details.id, historyVersion) { library.trackHistory(details.id) },
                streamMetadata = if (details.id == currentId) streamMetadata else emptyList(),
                favorite = details.id in favorites,
                onPrevious = {
                    adjacentStation(catalog.stations, details.id, -1)?.let {
                        play(controller, repository, it)
                        detailsId = it.id
                    }
                },
                onPlayPause = {
                    if (details.id != currentId) play(controller, repository, details)
                    else if (controller?.isPlaying == true) controller.pause() else controller?.play()
                },
                onStop = { controller?.stop() },
                onNext = {
                    adjacentStation(catalog.stations, details.id, 1)?.let {
                        play(controller, repository, it)
                        detailsId = it.id
                    }
                },
                onFavorite = { library.toggleFavorite(details.id); favoriteVersion++ }
            )
        } else {
            when (tab) {
                AppTab.HOME -> AllStationsScreen(
                    modifier = Modifier.padding(padding),
                    stations = catalog.stations,
                    favorites = favorites,
                    hiddenCount = hiddenCount,
                    onRestoreHidden = { repository.restoreHiddenStations() },
                    onStation = {
                        play(controller, repository, it)
                        detailsId = it.id
                    },
                    onFavorite = { library.toggleFavorite(it); favoriteVersion++ }
                )
                AppTab.ALL -> AllStationsScreen(
                    modifier = Modifier.padding(padding),
                    stations = catalog.stations,
                    favorites = favorites,
                    hiddenCount = hiddenCount,
                    onRestoreHidden = { repository.restoreHiddenStations() },
                    onStation = {
                        play(controller, repository, it)
                        detailsId = it.id
                    },
                    onFavorite = { library.toggleFavorite(it); favoriteVersion++ }
                )
                AppTab.FAVORITES -> StationsList(
                    modifier = Modifier.padding(padding),
                    title = "Ulubione",
                    subtitle = "Twoje zapisane stacje",
                    stations = catalog.stations.filter { it.id in favorites },
                    favorites = favorites,
                    onStation = {
                        play(controller, repository, it)
                        detailsId = it.id
                    },
                    onFavorite = { library.toggleFavorite(it); favoriteVersion++ }
                )
                AppTab.WEATHER -> WeatherHubScreen(
                    modifier = Modifier.padding(padding)
                )
                AppTab.MORE -> MoreScreen(
                    modifier = Modifier.padding(padding),
                    favoriteCount = favorites.size,
                    hiddenCount = hiddenCount,
                    onFavorites = { tab = AppTab.FAVORITES },
                    onAddStation = { addingCustomStation = true },
                    onRestoreHidden = { repository.restoreHiddenStations() },
                    onBackupRestored = {
                        restoredVersion++
                        favoriteVersion++
                        repository.reloadOverrides()
                    }
                )
            }
        }
    }

    editingStation?.let { station ->
        StationEditorDialog(
            station = station,
            title = if (repository.isCustomStation(station.id)) "Edytuj własną stację" else "Edytuj stację",
            canReset = repository.isEdited(station.id),
            canDelete = true,
            deleteLabel = if (repository.isCustomStation(station.id)) "Usuń stację" else "Usuń z listy",
            onDismiss = { editingStation = null },
            onSave = { edited ->
                repository.saveEditedStation(edited)
                if (edited.id == currentId) play(controller, repository, edited)
                editingStation = null
            },
            onReset = {
                val id = station.id
                repository.resetEditedStation(id)
                repository.find(id)?.let { restored ->
                    if (id == currentId) play(controller, repository, restored)
                }
                editingStation = null
            },
            onDelete = {
                val id = station.id
                if (id == currentId) controller?.stop()
                repository.removeStationFromList(id)
                editingStation = null
                detailsId = null
            }
        )
    }

    if (addingCustomStation) {
        StationEditorDialog(
            station = Station(
                id = "custom-new",
                name = "",
                streamUrl = "",
                category = "Własne",
                state = ""
            ),
            title = "Dodaj własną stację",
            canReset = false,
            canDelete = false,
            deleteLabel = "Usuń",
            onDismiss = { addingCustomStation = false },
            onSave = { draft ->
                val created = repository.createCustomStation(
                    name = draft.name,
                    streamUrl = draft.streamUrl,
                    logoUrl = draft.logoUrl,
                    homepage = draft.homepage,
                    category = draft.category,
                    state = draft.state,
                )
                addingCustomStation = false
                detailsId = created.id
            },
            onReset = {},
            onDelete = {}
        )
    }

}

private fun play(controller: MediaController?, repository: StationRepository, station: Station) {
    controller ?: return
    repository.trackClick(station.id)
    controller.setMediaItem(station.toMediaItem())
    controller.prepare()
    controller.play()
}

@Composable
private fun neonNavigationColors() = NavigationBarItemDefaults.colors(
    selectedIconColor = RadioCyan,
    selectedTextColor = RadioCyan,
    indicatorColor = RadioCyan.copy(alpha = .12f),
    unselectedIconColor = Color.White.copy(alpha = .58f),
    unselectedTextColor = Color.White.copy(alpha = .58f),
)

@Composable
private fun WeatherHubScreen(modifier: Modifier) {
    LazyColumn(
        modifier = modifier.fillMaxSize(),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        item {
            NeonSectionHeader(
                eyebrow = "W TRASIE",
                title = "Pogoda i komunikaty",
                subtitle = "Bieżąca pogoda, RSO, Alert RCB i informacje drogowe w jednym miejscu."
            )
        }
        item { WeatherPanel() }
        item { SafetyAlertsPanel() }
        item { RoadAssistPanel() }
    }
}

@Composable
private fun MoreScreen(
    modifier: Modifier,
    favoriteCount: Int,
    hiddenCount: Int,
    onFavorites: () -> Unit,
    onAddStation: () -> Unit,
    onRestoreHidden: () -> Unit,
    onBackupRestored: () -> Unit,
) {
    LazyColumn(
        modifier = modifier.fillMaxSize(),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        item {
            NeonSectionHeader(
                eyebrow = "RADIODRIVE",
                title = "Twoje radio",
                subtitle = "Własne stacje, lokalny backup i pełna kontrola nad katalogiem."
            )
        }
        item { LocalBackupPanel(onRestored = onBackupRestored) }
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                DashboardAction(
                    modifier = Modifier.weight(1f),
                    icon = Icons.Rounded.Favorite,
                    title = "Ulubione",
                    subtitle = "$favoriteCount stacji",
                    onClick = onFavorites
                )
                DashboardAction(
                    modifier = Modifier.weight(1f),
                    icon = Icons.Rounded.AddCircle,
                    title = "Własny stream",
                    subtitle = "Dodaj stację",
                    onClick = onAddStation
                )
            }
        }
        if (hiddenCount > 0) {
            item {
                DashboardAction(
                    modifier = Modifier.fillMaxWidth(),
                    icon = Icons.Rounded.Restore,
                    title = "Przywróć ukryte stacje",
                    subtitle = "$hiddenCount stacji możesz ponownie pokazać w katalogu",
                    onClick = onRestoreHidden
                )
            }
        }
        item {
            Surface(shape = RoundedCornerShape(24.dp), color = Color(0xFF0A1622)) {
                Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text("Lokalna kopia obejmuje", fontWeight = FontWeight.Black, color = RadioCyan)
                    listOf(
                        "własne stacje i adresy streamów",
                        "zmienione logotypy i dane stacji",
                        "ulubione oraz historię słuchania",
                        "ukryte i usunięte z listy stacje"
                    ).forEach {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Rounded.CheckCircle, null, tint = RadioCyan, modifier = Modifier.size(18.dp))
                            Spacer(Modifier.width(8.dp))
                            Text(it, color = Color.White.copy(alpha = .78f))
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun DashboardAction(
    modifier: Modifier,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    title: String,
    subtitle: String,
    onClick: () -> Unit,
) {
    Surface(
        modifier = modifier.clickable(onClick = onClick),
        shape = RoundedCornerShape(24.dp),
        color = Color(0xFF0D1A28),
        border = androidx.compose.foundation.BorderStroke(1.dp, Color.White.copy(alpha = .06f))
    ) {
        Column(Modifier.padding(16.dp)) {
            Surface(shape = CircleShape, color = RadioCyan.copy(alpha = .11f)) {
                Icon(icon, null, Modifier.padding(9.dp), tint = RadioCyan)
            }
            Spacer(Modifier.height(12.dp))
            Text(title, fontWeight = FontWeight.Black)
            Text(subtitle, style = MaterialTheme.typography.bodySmall, color = Color.White.copy(alpha = .55f))
        }
    }
}

@Composable
private fun NeonSectionHeader(eyebrow: String, title: String, subtitle: String) {
    Column {
        Text(eyebrow, color = RadioCyan, style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Black)
        Text(title, style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Black)
        Text(subtitle, color = Color.White.copy(alpha = .58f), style = MaterialTheme.typography.bodyMedium)
    }
}

@Composable
private fun HomeScreen(
    modifier: Modifier,
    catalog: List<Station>,
    current: Station?,
    isPlaying: Boolean,
    liveTitle: String?,
    favorites: Set<String>,
    error: String?,
    onStation: (Station) -> Unit,
    onDetails: () -> Unit,
) {
    val popular = remember(catalog) { catalog.take(24) }
    LazyColumn(
        modifier = modifier.fillMaxSize(),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        item { NowPlayingHero(current, isPlaying, liveTitle, onDetails) }
        item { WeatherPanel() }
        if (error != null) {
            item {
                Surface(shape = RoundedCornerShape(18.dp), color = MaterialTheme.colorScheme.errorContainer) {
                    Text(error, Modifier.padding(14.dp), color = MaterialTheme.colorScheme.onErrorContainer)
                }
            }
        }
        item {
            Text("Najpopularniejsze w Polsce", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Black)
            Text("Dotknij kafelka, aby rozpocząć słuchanie", color = MaterialTheme.colorScheme.onSurfaceVariant)
            Spacer(Modifier.height(10.dp))
            LazyRow(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                items(popular, key = { it.id }) { station ->
                    StationTile(
                        station = station,
                        active = station.id == current?.id,
                        favorite = station.id in favorites,
                        modifier = Modifier.width(164.dp),
                        onClick = { onStation(station) },
                        onFavorite = null
                    )
                }
            }
        }
    }
}

@Composable
private fun NowPlayingHero(current: Station?, isPlaying: Boolean, liveTitle: String?, onDetails: () -> Unit) {
    val gradient = Brush.linearGradient(
        listOf(
            Color(0xFF052A42),
            Color(0xFF0A2030),
            Color(0xFF3B2600)
        )
    )
    Surface(
        modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(30.dp)).clickable(enabled = current != null, onClick = onDetails),
        shape = RoundedCornerShape(30.dp),
        color = Color.Transparent
    ) {
        Column(Modifier.background(gradient).padding(20.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                StationLogo(current, 82.dp)
                Spacer(Modifier.width(16.dp))
                Column(Modifier.weight(1f)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Surface(shape = CircleShape, color = if (isPlaying) RadioCyan.copy(alpha = .18f) else Color.White.copy(alpha = .08f)) {
                            Text(if (isPlaying) "  LIVE  " else "  GOTOWE  ", Modifier.padding(vertical = 5.dp), color = if (isPlaying) RadioCyan else Color.White, fontWeight = FontWeight.Bold)
                        }
                    }
                    Spacer(Modifier.height(8.dp))
                    Text(current?.name ?: "Wybierz stację", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Black, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    Text(liveTitle ?: current?.subtitle ?: "Pełny katalog polskiego radia", maxLines = 2, overflow = TextOverflow.Ellipsis, color = Color.White.copy(alpha = .75f))
                }
                Icon(Icons.Rounded.ChevronRight, null, tint = Color.White.copy(alpha = .7f))
            }
        }
    }
}

@Composable
private fun AllStationsScreen(
    modifier: Modifier,
    stations: List<Station>,
    favorites: Set<String>,
    hiddenCount: Int,
    onRestoreHidden: () -> Unit,
    onStation: (Station) -> Unit,
    onFavorite: (String) -> Unit,
) {
    var query by rememberSaveable { mutableStateOf("") }
    var category by rememberSaveable { mutableStateOf<String?>(null) }
    var quickFilter by rememberSaveable { mutableStateOf("ALL") }

    val categories = remember(stations) { stations.map { it.category }.distinct().sorted() }
    val filtered = remember(stations, favorites, query, category, quickFilter) {
        stations.filter { station ->
            val quickOk = when (quickFilter) {
                "FAV" -> station.id in favorites
                "CUSTOM" -> station.id.startsWith("custom-")
                else -> true
            }
            quickOk &&
                (category == null || station.category == category) &&
                (query.isBlank() ||
                    station.name.contains(query, true) ||
                    station.state.contains(query, true) ||
                    station.tags.any { it.contains(query, true) })
        }
    }

    Column(modifier.fillMaxSize().padding(horizontal = 14.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text("Lista stacji", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Black)
                Text(
                    "${filtered.size} z ${stations.size} aktywnych stacji",
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            if (hiddenCount > 0) {
                IconButton(onClick = onRestoreHidden) {
                    Icon(Icons.Rounded.Restore, "Przywróć ukryte stacje", tint = RadioCyan)
                }
            }
        }

        Spacer(Modifier.height(8.dp))
        LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            item {
                FilterChip(
                    selected = quickFilter == "ALL",
                    onClick = { quickFilter = "ALL"; category = null },
                    label = { Text("Wszystkie") }
                )
            }
            item {
                FilterChip(
                    selected = quickFilter == "FAV",
                    onClick = { quickFilter = "FAV"; category = null },
                    label = { Text("Ulubione") }
                )
            }
            item {
                FilterChip(
                    selected = quickFilter == "CUSTOM",
                    onClick = { quickFilter = "CUSTOM"; category = null },
                    label = { Text("Własne") }
                )
            }
            item {
                FilterChip(
                    selected = quickFilter == "GENRE",
                    onClick = { quickFilter = "GENRE" },
                    label = { Text("Gatunki") }
                )
            }
        }

        Spacer(Modifier.height(8.dp))
        OutlinedTextField(
            value = query,
            onValueChange = { query = it },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            shape = RoundedCornerShape(18.dp),
            leadingIcon = { Icon(Icons.Rounded.Search, null) },
            placeholder = { Text("Szukaj stacji, miasta lub gatunku") }
        )

        if (quickFilter == "GENRE") {
            Spacer(Modifier.height(8.dp))
            LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                item {
                    FilterChip(
                        selected = category == null,
                        onClick = { category = null },
                        label = { Text("Wszystkie gatunki") }
                    )
                }
                items(categories) { item ->
                    FilterChip(
                        selected = category == item,
                        onClick = { category = if (category == item) null else item },
                        label = { Text(item) }
                    )
                }
            }
        }

        Spacer(Modifier.height(10.dp))
        LazyVerticalGrid(
            columns = GridCells.Adaptive(minSize = 142.dp),
            modifier = Modifier.weight(1f),
            contentPadding = PaddingValues(bottom = 18.dp),
            horizontalArrangement = Arrangement.spacedBy(10.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            gridItems(filtered, key = { it.id }) { station ->
                StationTile(
                    station = station,
                    active = false,
                    favorite = station.id in favorites,
                    onClick = { onStation(station) },
                    onFavorite = { onFavorite(station.id) }
                )
            }
        }
    }
}

@Composable
private fun StationsList(
    modifier: Modifier,
    title: String,
    subtitle: String,
    stations: List<Station>,
    favorites: Set<String>,
    onStation: (Station) -> Unit,
    onFavorite: (String) -> Unit,
) {
    Column(modifier.fillMaxSize().padding(horizontal = 14.dp)) {
        Text(title, style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Black)
        Text(subtitle, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(Modifier.height(10.dp))
        if (stations.isEmpty()) {
            Surface(shape = RoundedCornerShape(22.dp), color = MaterialTheme.colorScheme.surfaceVariant) {
                Text("Nie masz jeszcze zapisanych stacji.", Modifier.fillMaxWidth().padding(20.dp))
            }
        } else {
            LazyVerticalGrid(
                columns = GridCells.Adaptive(minSize = 148.dp),
                modifier = Modifier.weight(1f),
                contentPadding = PaddingValues(bottom = 18.dp),
                horizontalArrangement = Arrangement.spacedBy(10.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                gridItems(stations, key = { it.id }) { station ->
                    StationTile(
                        station = station,
                        active = false,
                        favorite = station.id in favorites,
                        onClick = { onStation(station) },
                        onFavorite = { onFavorite(station.id) }
                    )
                }
            }
        }
    }
}

@Composable
private fun StationTile(
    station: Station,
    active: Boolean,
    favorite: Boolean,
    modifier: Modifier = Modifier,
    onClick: () -> Unit,
    onFavorite: (() -> Unit)?,
) {
    Surface(
        modifier = modifier
            .clip(RoundedCornerShape(24.dp))
            .clickable(onClick = onClick),
        shape = RoundedCornerShape(24.dp),
        color = if (active) RadioCyan.copy(alpha = .10f) else Color(0xFF0D1926),
        border = androidx.compose.foundation.BorderStroke(
            1.dp,
            if (active) RadioCyan.copy(alpha = .55f) else Color.White.copy(alpha = .06f)
        ),
        tonalElevation = if (active) 4.dp else 1.dp
    ) {
        Column(Modifier.padding(12.dp)) {
            Box {
                StationLogo(station, 112.dp)
                if (station.lastCheckOk) {
                    Box(
                        Modifier
                            .align(Alignment.TopEnd)
                            .padding(7.dp)
                            .size(11.dp)
                            .clip(CircleShape)
                            .background(RadioCyan)
                    )
                }
            }
            Spacer(Modifier.height(10.dp))
            Text(station.name, fontWeight = FontWeight.Black, maxLines = 2, overflow = TextOverflow.Ellipsis)
            Text(
                station.state.ifBlank { station.category },
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    buildString {
                        if (station.codec.isNotBlank()) append(station.codec)
                        if (station.bitrate > 0) {
                            if (isNotEmpty()) append(" • ")
                            append("${station.bitrate} kb/s")
                        }
                    }.ifBlank { "LIVE" },
                    style = MaterialTheme.typography.labelSmall,
                    color = RadioAmber,
                    modifier = Modifier.weight(1f)
                )
                if (onFavorite != null) {
                    IconButton(onClick = onFavorite, modifier = Modifier.size(34.dp)) {
                        Icon(
                            if (favorite) Icons.Rounded.Favorite else Icons.Rounded.FavoriteBorder,
                            null,
                            tint = if (favorite) RadioAmber else MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun StationRow(
    station: Station,
    active: Boolean,
    favorite: Boolean,
    onClick: () -> Unit,
    onFavorite: (() -> Unit)?,
) {
    Surface(
        modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(22.dp)).clickable(onClick = onClick),
        shape = RoundedCornerShape(22.dp),
        color = if (active) MaterialTheme.colorScheme.primary.copy(alpha = .10f) else MaterialTheme.colorScheme.surface,
        tonalElevation = 1.dp
    ) {
        Row(Modifier.padding(10.dp), verticalAlignment = Alignment.CenterVertically) {
            StationLogo(station, 62.dp)
            Spacer(Modifier.width(12.dp))
            Column(Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    if (station.lastCheckOk) {
                        Box(Modifier.size(7.dp).clip(CircleShape).background(RadioCyan))
                        Spacer(Modifier.width(6.dp))
                    }
                    Text(station.name, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                }
                Text(station.subtitle.ifBlank { "Polska • ${station.category}" }, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text(buildString {
                    if (station.codec.isNotBlank()) append(station.codec)
                    if (station.bitrate > 0) {
                        if (isNotEmpty()) append(" • ")
                        append("${station.bitrate} kb/s")
                    }
                    if (station.hls) append(" • HLS")
                }, style = MaterialTheme.typography.labelSmall, color = RadioAmber)
            }
            if (onFavorite != null) IconButton(onClick = onFavorite) {
                Icon(if (favorite) Icons.Rounded.Favorite else Icons.Rounded.FavoriteBorder, null, tint = if (favorite) RadioAmber else MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

@Composable
private fun PlayerDetailsScreen(
    modifier: Modifier,
    station: Station,
    isCurrent: Boolean,
    isPlaying: Boolean,
    isBuffering: Boolean,
    liveTitle: String?,
    liveArtist: String?,
    history: List<String>,
    streamMetadata: List<String>,
    favorite: Boolean,
    onPrevious: () -> Unit,
    onPlayPause: () -> Unit,
    onStop: () -> Unit,
    onNext: () -> Unit,
    onFavorite: () -> Unit,
) {
    val context = LocalContext.current
    Box(modifier.fillMaxSize()) {
        if (!station.logoUrl.isNullOrBlank()) {
            AsyncImage(
                model = station.logoUrl,
                contentDescription = null,
                modifier = Modifier.matchParentSize().blur(56.dp).alpha(.20f),
                contentScale = ContentScale.Crop
            )
        }
        Box(
            Modifier
                .matchParentSize()
                .background(
                    Brush.verticalGradient(
                        listOf(
                            Color(0xFF06111D).copy(alpha = .80f),
                            Color(0xFF07111C).copy(alpha = .96f),
                            MaterialTheme.colorScheme.background
                        )
                    )
                )
        )
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(14.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            item {
                Surface(
                    shape = RoundedCornerShape(30.dp),
                    color = Color(0xFF0A1724).copy(alpha = .94f),
                    border = androidx.compose.foundation.BorderStroke(1.dp, RadioCyan.copy(alpha = .28f)),
                    shadowElevation = 8.dp
                ) {
                    Column(Modifier.fillMaxWidth().padding(16.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            StationLogo(station, 128.dp)
                            Spacer(Modifier.width(16.dp))
                            Column(Modifier.weight(1f)) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Surface(
                                        shape = CircleShape,
                                        color = if (isCurrent && isPlaying) RadioCyan.copy(alpha = .15f) else Color.White.copy(alpha = .07f)
                                    ) {
                                        Text(
                                            if (isBuffering) " BUFOROWANIE " else if (isCurrent && isPlaying) " ● LIVE " else " ONLINE ",
                                            Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                                            color = if (isCurrent && isPlaying) RadioCyan else Color.White.copy(alpha = .75f),
                                            style = MaterialTheme.typography.labelSmall,
                                            fontWeight = FontWeight.Black
                                        )
                                    }
                                    Spacer(Modifier.weight(1f))
                                    IconButton(onClick = onFavorite, modifier = Modifier.size(34.dp)) {
                                        Icon(
                                            if (favorite) Icons.Rounded.Favorite else Icons.Rounded.FavoriteBorder,
                                            "Ulubione",
                                            tint = if (favorite) RadioAmber else Color.White.copy(alpha = .75f)
                                        )
                                    }
                                }
                                Spacer(Modifier.height(6.dp))
                                Text(
                                    station.name,
                                    style = MaterialTheme.typography.headlineSmall,
                                    fontWeight = FontWeight.Black,
                                    maxLines = 2,
                                    overflow = TextOverflow.Ellipsis
                                )
                                Text(
                                    liveTitle ?: station.subtitle.ifBlank { "Polska" },
                                    color = RadioCyan,
                                    style = MaterialTheme.typography.titleSmall,
                                    fontWeight = FontWeight.Bold,
                                    maxLines = 2,
                                    overflow = TextOverflow.Ellipsis
                                )
                                liveArtist?.let {
                                    Text(
                                        it,
                                        color = Color.White.copy(alpha = .66f),
                                        style = MaterialTheme.typography.bodySmall,
                                        maxLines = 1,
                                        overflow = TextOverflow.Ellipsis
                                    )
                                }
                                Spacer(Modifier.height(7.dp))
                                Row(horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                                    if (station.bitrate > 0) TinyDataChip("${station.bitrate} kbps")
                                    if (station.codec.isNotBlank()) TinyDataChip(station.codec)
                                    TinyDataChip(if (station.hls) "HLS" else "LIVE")
                                }
                                Spacer(Modifier.height(9.dp))
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    IconButton(onClick = onPrevious, modifier = Modifier.size(38.dp)) {
                                        Icon(Icons.Rounded.SkipPrevious, "Poprzednia stacja")
                                    }
                                    FilledIconButton(
                                        onClick = onPlayPause,
                                        modifier = Modifier.size(46.dp),
                                        colors = IconButtonDefaults.filledIconButtonColors(
                                            containerColor = RadioCyan,
                                            contentColor = Color(0xFF001B24)
                                        )
                                    ) {
                                        Icon(
                                            if (isCurrent && isPlaying) Icons.Rounded.Pause else Icons.Rounded.PlayArrow,
                                            "Odtwarzaj / pauza"
                                        )
                                    }
                                    IconButton(onClick = onStop, modifier = Modifier.size(38.dp)) {
                                        Icon(Icons.Rounded.Stop, "Zatrzymaj")
                                    }
                                    IconButton(onClick = onNext, modifier = Modifier.size(38.dp)) {
                                        Icon(Icons.Rounded.SkipNext, "Następna stacja")
                                    }
                                }

                                Spacer(Modifier.height(10.dp))
                                CompactWeatherInline()
                            }
                        }
                    }
                }
            }

            item { SafetyAlertsPanel() }

            item {
                InfoPanel(
                    icon = Icons.Rounded.SkipNext,
                    title = "RAMÓWKA / CO DALEJ",
                    main = "Informacje tylko ze źródeł nadawcy",
                    secondary = "Jeżeli stacja publikuje ramówkę lub dane „co gramy”, RadioDrive wykorzystuje je bez zgadywania.",
                    accent = false
                )
            }

            item { RoadAssistPanel() }
            item { StationWebInfoPanel(station) }

            if (streamMetadata.isNotEmpty()) {
                item {
                    Surface(shape = RoundedCornerShape(24.dp), color = MaterialTheme.colorScheme.surfaceVariant) {
                        Column(Modifier.fillMaxWidth().padding(18.dp)) {
                            Text("Metadane ze strumienia", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Black)
                            Text(
                                "ICY / ID3 / HLS — wszystko, co rzeczywiście przekazuje nadawca.",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                            Spacer(Modifier.height(8.dp))
                            streamMetadata.forEach { entry ->
                                Text("• $entry", style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(vertical = 2.dp))
                            }
                        }
                    }
                }
            }

            item {
                Text("Informacje o transmisji", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Black)
                Spacer(Modifier.height(8.dp))
                LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    item { DataChip("Jakość", station.streamQuality) }
                    if (station.codec.isNotBlank()) item { DataChip("Kodek", station.codec) }
                    if (station.bitrate > 0) item { DataChip("Bitrate", "${station.bitrate} kb/s") }
                    item { DataChip("Tryb", if (station.hls) "HLS" else "Live stream") }
                    if (station.state.isNotBlank()) item { DataChip("Region", station.state) }
                }
            }

            if (history.isNotEmpty()) {
                item {
                    Text("Ostatnio na antenie", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Black)
                    Text("Historia metadanych odebranych ze strumienia", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Spacer(Modifier.height(8.dp))
                    history.take(8).forEachIndexed { index, entry ->
                        Row(Modifier.fillMaxWidth().padding(vertical = 7.dp), verticalAlignment = Alignment.CenterVertically) {
                            Text("${index + 1}", color = RadioAmber, fontWeight = FontWeight.Black, modifier = Modifier.width(28.dp))
                            Text(entry, modifier = Modifier.weight(1f), maxLines = 2, overflow = TextOverflow.Ellipsis)
                        }
                        HorizontalDivider()
                    }
                }
            }
        }
    }
}

@Composable
private fun TinyDataChip(text: String) {
    Surface(
        shape = RoundedCornerShape(12.dp),
        color = Color.White.copy(alpha = .06f),
        border = androidx.compose.foundation.BorderStroke(1.dp, Color.White.copy(alpha = .08f))
    ) {
        Text(
            text,
            modifier = Modifier.padding(horizontal = 7.dp, vertical = 3.dp),
            style = MaterialTheme.typography.labelSmall,
            color = Color.White.copy(alpha = .72f)
        )
    }
}

@Composable
private fun InfoPanel(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    title: String,
    main: String,
    secondary: String,
    accent: Boolean,
) {
    Surface(
        shape = RoundedCornerShape(24.dp),
        color = if (accent) RadioCyan.copy(alpha = .09f) else MaterialTheme.colorScheme.surfaceVariant
    ) {
        Row(Modifier.padding(18.dp), verticalAlignment = Alignment.Top) {
            Surface(shape = CircleShape, color = if (accent) RadioCyan.copy(alpha = .16f) else MaterialTheme.colorScheme.surface) {
                Icon(icon, null, Modifier.padding(10.dp), tint = if (accent) RadioCyan else RadioAmber)
            }
            Spacer(Modifier.width(14.dp))
            Column {
                Text(title, style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Black, color = if (accent) RadioCyan else RadioAmber)
                Text(main, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                Spacer(Modifier.height(4.dp))
                Text(secondary, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

@Composable
private fun DataChip(label: String, value: String) {
    Surface(shape = RoundedCornerShape(18.dp), color = MaterialTheme.colorScheme.surfaceVariant) {
        Column(Modifier.padding(horizontal = 14.dp, vertical = 10.dp)) {
            Text(label.uppercase(), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(value, fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
private fun StationLogo(station: Station?, size: androidx.compose.ui.unit.Dp) {
    Surface(shape = RoundedCornerShape(24.dp), color = MaterialTheme.colorScheme.surfaceVariant) {
        Box(Modifier.size(size), contentAlignment = Alignment.Center) {
            if (!station?.logoUrl.isNullOrBlank()) {
                AsyncImage(
                    model = station?.logoUrl,
                    contentDescription = station?.name,
                    modifier = Modifier.fillMaxSize().padding(7.dp).clip(RoundedCornerShape(18.dp)),
                    contentScale = ContentScale.Fit
                )
            } else {
                Text(station?.name?.take(2)?.uppercase() ?: "RD", fontWeight = FontWeight.Black, color = RadioAmber)
            }
        }
    }
}


private fun prettifyStreamMetadata(raw: String): String? {
    val text = raw.trim().replace(Regex("\\s+"), " ")
    if (text.isBlank() || text.length > 600) return null

    val preferred = Regex(
        """(?i)(?:streamtitle|title|artist|album|description|text|value)\s*=\s*["']?([^,"'}\]]{2,220})"""
    ).findAll(text)
        .map { match -> match.groupValues[1].trim() }
        .filter { it.isNotBlank() }
        .distinct()
        .joinToString(" • ")

    if (preferred.isNotBlank()) return preferred.take(240)

    val cleaned = text
        .replace(Regex("""^[A-Za-z0-9_.$]+\s*[:{(]\s*"""), "")
        .trim('}', ')', ' ', '"', '\'')

    return cleaned.takeIf {
        it.length in 3..220 &&
            !it.contains("@") &&
            !it.matches(Regex("""[0-9a-fA-F]{32,}"""))
    }
}


@Composable
private fun StickyMiniPlayer(
    station: Station,
    isPlaying: Boolean,
    isBuffering: Boolean,
    liveTitle: String?,
    favorite: Boolean,
    onOpen: () -> Unit,
    onPrevious: () -> Unit,
    onPlayPause: () -> Unit,
    onStop: () -> Unit,
    onNext: () -> Unit,
    onFavorite: () -> Unit,
) {
    Surface(
        tonalElevation = 6.dp,
        shadowElevation = 8.dp,
        color = MaterialTheme.colorScheme.surface
    ) {
        Column(
            Modifier
                .fillMaxWidth()
                .clickable(onClick = onOpen)
                .padding(horizontal = 10.dp, vertical = 8.dp)
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                StationLogo(station, 48.dp)
                Spacer(Modifier.width(10.dp))
                Column(Modifier.weight(1f)) {
                    Text(
                        station.name,
                        fontWeight = FontWeight.Black,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                    Text(
                        if (isBuffering) "Buforowanie…" else liveTitle ?: if (isPlaying) "LIVE" else "Wstrzymano",
                        style = MaterialTheme.typography.bodySmall,
                        color = if (isPlaying) RadioCyan else MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                }
                IconButton(onClick = onFavorite, modifier = Modifier.size(38.dp)) {
                    Icon(
                        if (favorite) Icons.Rounded.Favorite else Icons.Rounded.FavoriteBorder,
                        "Ulubione",
                        tint = if (favorite) RadioAmber else MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceEvenly,
                verticalAlignment = Alignment.CenterVertically
            ) {
                IconButton(onClick = onPrevious) { Icon(Icons.Rounded.SkipPrevious, "Poprzednia stacja") }
                FilledIconButton(
                    onClick = onPlayPause,
                    modifier = Modifier.size(44.dp),
                    colors = IconButtonDefaults.filledIconButtonColors(
                        containerColor = RadioAmber,
                        contentColor = Color(0xFF201400)
                    )
                ) {
                    Icon(if (isPlaying) Icons.Rounded.Pause else Icons.Rounded.PlayArrow, "Odtwarzaj lub pauza")
                }
                IconButton(onClick = onStop) { Icon(Icons.Rounded.Stop, "Zatrzymaj") }
                IconButton(onClick = onNext) { Icon(Icons.Rounded.SkipNext, "Następna stacja") }
                IconButton(onClick = onOpen) { Icon(Icons.Rounded.OpenInFull, "Pełny odtwarzacz") }
            }
        }
    }
}

private fun adjacentStation(stations: List<Station>, currentId: String, delta: Int): Station? {
    if (stations.isEmpty()) return null
    val current = stations.indexOfFirst { it.id == currentId }.takeIf { it >= 0 } ?: 0
    val next = (current + delta).floorMod(stations.size)
    return stations.getOrNull(next)
}

private fun Int.floorMod(size: Int): Int = ((this % size) + size) % size

@Composable
private fun StationEditorDialog(
    station: Station,
    title: String,
    canReset: Boolean,
    canDelete: Boolean,
    deleteLabel: String,
    onDismiss: () -> Unit,
    onSave: (Station) -> Unit,
    onReset: () -> Unit,
    onDelete: () -> Unit,
) {
    var name by remember(station.id) { mutableStateOf(station.name) }
    var streamUrl by remember(station.id) { mutableStateOf(station.streamUrl) }
    var logoUrl by remember(station.id) { mutableStateOf(station.logoUrl.orEmpty()) }
    var homepage by remember(station.id) { mutableStateOf(station.homepage.orEmpty()) }
    var category by remember(station.id) { mutableStateOf(station.category) }
    var state by remember(station.id) { mutableStateOf(station.state) }
    var confirmDelete by remember(station.id) { mutableStateOf(false) }

    val streamOk = streamUrl.trim().startsWith("http://") || streamUrl.trim().startsWith("https://")
    val logoOk = logoUrl.isBlank() || logoUrl.trim().startsWith("http://") || logoUrl.trim().startsWith("https://")
    val homepageOk = homepage.isBlank() || homepage.trim().startsWith("http://") || homepage.trim().startsWith("https://")
    val canSave = name.isNotBlank() && streamOk && logoOk && homepageOk

    androidx.compose.ui.window.Dialog(
        onDismissRequest = onDismiss,
        properties = androidx.compose.ui.window.DialogProperties(usePlatformDefaultWidth = false)
    ) {
        Surface(
            modifier = Modifier.fillMaxSize(),
            color = Color(0xFF07111C)
        ) {
            Column(Modifier.fillMaxSize()) {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    IconButton(onClick = onDismiss) {
                        Icon(Icons.Rounded.ArrowBack, "Wróć")
                    }
                    Column(Modifier.weight(1f)) {
                        Text(title, fontWeight = FontWeight.Black, style = MaterialTheme.typography.titleLarge)
                        Text(
                            if (station.id == "custom-new") "NOWA STACJA" else "USTAWIENIA STACJI",
                            color = RadioCyan,
                            style = MaterialTheme.typography.labelSmall,
                            fontWeight = FontWeight.Black
                        )
                    }
                    FilledIconButton(
                        onClick = {
                            onSave(
                                station.copy(
                                    name = name.trim(),
                                    streamUrl = streamUrl.trim(),
                                    logoUrl = logoUrl.trim().takeIf { it.isNotBlank() },
                                    homepage = homepage.trim().takeIf { it.isNotBlank() },
                                    category = category.trim().ifBlank { "Różne" },
                                    state = state.trim(),
                                )
                            )
                        },
                        enabled = canSave,
                        colors = IconButtonDefaults.filledIconButtonColors(
                            containerColor = RadioCyan,
                            contentColor = Color(0xFF001B24)
                        )
                    ) {
                        Icon(Icons.Rounded.Check, "Zapisz")
                    }
                }

                HorizontalDivider(color = Color.White.copy(alpha = .08f))

                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    item {
                        Surface(
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(26.dp),
                            color = Color(0xFF0D1A28),
                            border = androidx.compose.foundation.BorderStroke(1.dp, Color.White.copy(alpha = .06f))
                        ) {
                            Row(
                                Modifier.fillMaxWidth().padding(16.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Surface(
                                    shape = RoundedCornerShape(20.dp),
                                    color = MaterialTheme.colorScheme.surfaceVariant
                                ) {
                                    if (logoUrl.isNotBlank()) {
                                        AsyncImage(
                                            model = logoUrl,
                                            contentDescription = "Podgląd logo",
                                            modifier = Modifier.size(96.dp).padding(8.dp),
                                            contentScale = ContentScale.Fit
                                        )
                                    } else {
                                        Box(Modifier.size(96.dp), contentAlignment = Alignment.Center) {
                                            Icon(Icons.Rounded.Radio, null, Modifier.size(40.dp), tint = RadioCyan)
                                        }
                                    }
                                }
                                Spacer(Modifier.width(14.dp))
                                Column(Modifier.weight(1f)) {
                                    Text("Logo stacji", fontWeight = FontWeight.Black)
                                    Text(
                                        "Wklej bezpośredni link HTTPS/HTTP do grafiki.",
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                }
                            }
                        }
                    }

                    item {
                        OutlinedTextField(
                            value = logoUrl,
                            onValueChange = { logoUrl = it },
                            label = { Text("Logo – zewnętrzny URL") },
                            isError = logoUrl.isNotBlank() && !logoOk,
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                    item {
                        OutlinedTextField(
                            value = name,
                            onValueChange = { name = it },
                            label = { Text("Nazwa stacji") },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                    item {
                        OutlinedTextField(
                            value = streamUrl,
                            onValueChange = { streamUrl = it },
                            label = { Text("Adres strumienia") },
                            supportingText = { Text("Bezpośredni publiczny URL MP3 / AAC / HLS") },
                            isError = streamUrl.isNotBlank() && !streamOk,
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                    item {
                        OutlinedTextField(
                            value = homepage,
                            onValueChange = { homepage = it },
                            label = { Text("Strona WWW (opcjonalnie)") },
                            isError = homepage.isNotBlank() && !homepageOk,
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                    item {
                        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                            OutlinedTextField(
                                value = category,
                                onValueChange = { category = it },
                                label = { Text("Kategoria") },
                                singleLine = true,
                                modifier = Modifier.weight(1f)
                            )
                            OutlinedTextField(
                                value = state,
                                onValueChange = { state = it },
                                label = { Text("Region") },
                                singleLine = true,
                                modifier = Modifier.weight(1f)
                            )
                        }
                    }
                    item {
                        Text(
                            if (station.id == "custom-new") {
                                "Własna stacja pojawi się w pełnym katalogu RadioDrive i Android Auto oraz będzie zapisywana w lokalnym backupie."
                            } else {
                                "Twoje zmiany mają pierwszeństwo nad danymi katalogowymi i nie znikną po odświeżeniu listy stacji."
                            },
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }

                    if (canReset || canDelete) {
                        item {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.spacedBy(10.dp)
                            ) {
                                if (canDelete) {
                                    OutlinedButton(
                                        onClick = { confirmDelete = true },
                                        modifier = Modifier.weight(1f),
                                        colors = ButtonDefaults.outlinedButtonColors(
                                            contentColor = MaterialTheme.colorScheme.error
                                        )
                                    ) {
                                        Icon(Icons.Rounded.Delete, null)
                                        Spacer(Modifier.width(6.dp))
                                        Text(deleteLabel)
                                    }
                                }
                                if (canReset) {
                                    OutlinedButton(
                                        onClick = onReset,
                                        modifier = Modifier.weight(1f)
                                    ) {
                                        Icon(Icons.Rounded.Restore, null)
                                        Spacer(Modifier.width(6.dp))
                                        Text("Przywróć")
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    if (confirmDelete) {
        AlertDialog(
            onDismissRequest = { confirmDelete = false },
            title = { Text(if (station.id.startsWith("custom-")) "Usunąć stację?" else "Usunąć stację z listy?") },
            text = {
                Text(
                    if (station.id.startsWith("custom-")) {
                        "Własna stacja zostanie usunięta. Nowy lokalny backup będzie już zapisywał stan bez tej stacji."
                    } else {
                        "Stacja zostanie ukryta w Twojej liście. W każdej chwili możesz użyć opcji „Przywróć ukryte”."
                    }
                )
            },
            confirmButton = {
                Button(
                    onClick = {
                        confirmDelete = false
                        onDelete()
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error)
                ) { Text("Usuń") }
            },
            dismissButton = {
                TextButton(onClick = { confirmDelete = false }) { Text("Anuluj") }
            }
        )
    }
}

