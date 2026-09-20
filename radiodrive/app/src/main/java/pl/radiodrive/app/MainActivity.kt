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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
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
import pl.radiodrive.app.data.StationRepository
import pl.radiodrive.app.data.UserLibrary
import pl.radiodrive.app.weather.WeatherPanel
import pl.radiodrive.app.model.Station
import pl.radiodrive.app.playback.RadioPlaybackService
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

private enum class AppTab { HOME, ALL, FAVORITES }

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
    var favoriteVersion by remember { mutableIntStateOf(0) }
    var historyVersion by remember { mutableIntStateOf(0) }

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
        }
        controller.addListener(listener)
        currentId = controller.currentMediaItem?.mediaId
        isPlaying = controller.isPlaying
        isBuffering = controller.playbackState == Player.STATE_BUFFERING
        onDispose { controller.removeListener(listener) }
    }

    val favorites = remember(favoriteVersion) { library.favorites() }
    val current = catalog.stations.firstOrNull { it.id == currentId }
    val details = catalog.stations.firstOrNull { it.id == detailsId }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    if (details != null) {
                        Column {
                            Text(details.name, maxLines = 1, overflow = TextOverflow.Ellipsis, fontWeight = FontWeight.Bold)
                            Text("RadioDrive • Polska", style = MaterialTheme.typography.labelSmall)
                        }
                    } else {
                        Column {
                            Text("RadioDrive", fontWeight = FontWeight.Black)
                            Text("v${BuildConfig.VERSION_NAME} • ${catalog.stations.size} aktywnych polskich stacji", style = MaterialTheme.typography.labelSmall)
                        }
                    }
                },
                navigationIcon = {
                    if (details != null) {
                        IconButton(onClick = { detailsId = null }) { Icon(Icons.Rounded.ArrowBack, "Wróć") }
                    }
                },
                actions = {
                    if (details == null) {
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
                NavigationBar {
                    NavigationBarItem(
                        selected = tab == AppTab.HOME,
                        onClick = { tab = AppTab.HOME },
                        icon = { Icon(Icons.Rounded.Home, null) },
                        label = { Text("Start") }
                    )
                    NavigationBarItem(
                        selected = tab == AppTab.ALL,
                        onClick = { tab = AppTab.ALL },
                        icon = { Icon(Icons.Rounded.Radio, null) },
                        label = { Text("Stacje") }
                    )
                    NavigationBarItem(
                        selected = tab == AppTab.FAVORITES,
                        onClick = { tab = AppTab.FAVORITES },
                        icon = { Icon(Icons.Rounded.Favorite, null) },
                        label = { Text("Ulubione") }
                    )
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
                favorite = details.id in favorites,
                onPlayPause = {
                    if (details.id != currentId) play(controller, repository, details)
                    else if (controller?.isPlaying == true) controller.pause() else controller?.play()
                },
                onFavorite = { library.toggleFavorite(details.id); favoriteVersion++ }
            )
        } else {
            when (tab) {
                AppTab.HOME -> HomeScreen(
                    modifier = Modifier.padding(padding),
                    catalog = catalog.stations,
                    current = current,
                    isPlaying = isPlaying,
                    liveTitle = liveTitle,
                    favorites = favorites,
                    error = catalog.error,
                    onStation = {
                        play(controller, repository, it)
                        detailsId = it.id
                    },
                    onDetails = { current?.let { detailsId = it.id } }
                )
                AppTab.ALL -> AllStationsScreen(
                    modifier = Modifier.padding(padding),
                    stations = catalog.stations,
                    favorites = favorites,
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
            }
        }
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
        item {
            NowPlayingHero(current, isPlaying, liveTitle, onDetails)
        }
        item {
            WeatherPanel()
        }
        if (error != null) {
            item {
                Surface(shape = RoundedCornerShape(18.dp), color = MaterialTheme.colorScheme.errorContainer) {
                    Text(error, Modifier.padding(14.dp), color = MaterialTheme.colorScheme.onErrorContainer)
                }
            }
        }
        item {
            Text("Najpopularniejsze w Polsce", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Black)
            Text("Aktywne strumienie posortowane według popularności katalogu", color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        items(popular, key = { it.id }) { station ->
            StationRow(station, station.id == current?.id, station.id in favorites, onClick = { onStation(station) }, onFavorite = null)
        }
    }
}

@Composable
private fun NowPlayingHero(current: Station?, isPlaying: Boolean, liveTitle: String?, onDetails: () -> Unit) {
    val gradient = Brush.linearGradient(listOf(Color(0xFF342100), Color(0xFF073B36), RadioSurface2))
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
    onStation: (Station) -> Unit,
    onFavorite: (String) -> Unit,
) {
    var query by rememberSaveable { mutableStateOf("") }
    var category by rememberSaveable { mutableStateOf<String?>(null) }
    val categories = remember(stations) { stations.map { it.category }.distinct().sorted() }
    val filtered = remember(stations, query, category) {
        stations.filter { s ->
            (category == null || s.category == category) &&
                (query.isBlank() ||
                    s.name.contains(query, true) ||
                    s.state.contains(query, true) ||
                    s.tags.any { it.contains(query, true) })
        }
    }

    LazyColumn(
        modifier = modifier.fillMaxSize(),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        item {
            Text("Wszystkie stacje", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Black)
            Text("${filtered.size} z ${stations.size} aktywnych stacji", color = MaterialTheme.colorScheme.onSurfaceVariant)
            Spacer(Modifier.height(12.dp))
            OutlinedTextField(
                value = query,
                onValueChange = { query = it },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                shape = RoundedCornerShape(18.dp),
                leadingIcon = { Icon(Icons.Rounded.Search, null) },
                placeholder = { Text("Nazwa, miasto, region lub gatunek") }
            )
            Spacer(Modifier.height(10.dp))
            LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                item {
                    FilterChip(selected = category == null, onClick = { category = null }, label = { Text("Wszystkie") })
                }
                items(categories) { c ->
                    FilterChip(selected = category == c, onClick = { category = if (category == c) null else c }, label = { Text(c) })
                }
            }
        }
        items(filtered, key = { it.id }) { station ->
            StationRow(station, false, station.id in favorites, onClick = { onStation(station) }, onFavorite = { onFavorite(station.id) })
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
    LazyColumn(modifier.fillMaxSize(), contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        item {
            Text(title, style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Black)
            Text(subtitle, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        if (stations.isEmpty()) item {
            Surface(shape = RoundedCornerShape(22.dp), color = MaterialTheme.colorScheme.surfaceVariant) {
                Text("Nie masz jeszcze zapisanych stacji.", Modifier.padding(20.dp))
            }
        }
        items(stations, key = { it.id }) { station ->
            StationRow(station, false, station.id in favorites, { onStation(station) }, { onFavorite(station.id) })
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
    favorite: Boolean,
    onPlayPause: () -> Unit,
    onFavorite: () -> Unit,
) {
    val context = LocalContext.current
    LazyColumn(
        modifier = modifier.fillMaxSize(),
        contentPadding = PaddingValues(18.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.fillMaxWidth()) {
                StationLogo(station, 150.dp)
                Spacer(Modifier.height(14.dp))
                Surface(shape = CircleShape, color = RadioCyan.copy(alpha = .14f)) {
                    Text(if (isBuffering) "  BUFOROWANIE  " else if (isCurrent && isPlaying) "  LIVE  " else "  ONLINE  ", Modifier.padding(vertical = 6.dp), color = RadioCyan, fontWeight = FontWeight.Black)
                }
                Spacer(Modifier.height(8.dp))
                Text(station.name, style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Black)
                Text(station.subtitle.ifBlank { "Polska" }, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Spacer(Modifier.height(16.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    FilledIconButton(onClick = onPlayPause, modifier = Modifier.size(64.dp), colors = IconButtonDefaults.filledIconButtonColors(containerColor = RadioAmber, contentColor = Color(0xFF201400))) {
                        Icon(if (isCurrent && isPlaying) Icons.Rounded.Pause else Icons.Rounded.PlayArrow, null, Modifier.size(34.dp))
                    }
                    FilledTonalIconButton(onClick = onFavorite, modifier = Modifier.size(64.dp)) {
                        Icon(if (favorite) Icons.Rounded.Favorite else Icons.Rounded.FavoriteBorder, null, tint = if (favorite) RadioAmber else MaterialTheme.colorScheme.onSurface)
                    }
                    if (station.homepage != null) FilledTonalIconButton(
                        onClick = { runCatching { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(station.homepage))) } },
                        modifier = Modifier.size(64.dp)
                    ) { Icon(Icons.Rounded.Language, "Strona stacji") }
                }
            }
        }

        item {
            InfoPanel(
                icon = Icons.Rounded.GraphicEq,
                title = "TERAZ GRAMY",
                main = liveTitle ?: "Stacja nie przekazuje tytułu audycji/utworu",
                secondary = liveArtist ?: "RadioDrive pokaże metadane automatycznie, gdy pojawią się w strumieniu.",
                accent = true
            )
        }

        item {
            InfoPanel(
                icon = Icons.Rounded.SkipNext,
                title = "NASTĘPNY",
                main = "Dane zależne od nadawcy",
                secondary = "Przyszły utwór lub program nie jest częścią standardowego strumienia radia. Pole uzupełnia się tylko dla stacji udostępniających ramówkę/EPG.",
                accent = false
            )
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

        if (station.tags.isNotEmpty()) item {
            Text("Gatunki i tagi", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(8.dp))
            LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                items(station.tags) { tag -> AssistChip(onClick = {}, label = { Text(tag) }) }
            }
        }

        if (history.isNotEmpty()) item {
            Text("Ostatnio na antenie", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Black)
            Text("Historia metadanych zapisana przez RadioDrive", color = MaterialTheme.colorScheme.onSurfaceVariant)
            Spacer(Modifier.height(8.dp))
            history.take(8).forEachIndexed { index, item ->
                Row(Modifier.fillMaxWidth().padding(vertical = 7.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text("${index + 1}", color = RadioAmber, fontWeight = FontWeight.Black, modifier = Modifier.width(28.dp))
                    Text(item, modifier = Modifier.weight(1f), maxLines = 2, overflow = TextOverflow.Ellipsis)
                }
                HorizontalDivider()
            }
        }
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
