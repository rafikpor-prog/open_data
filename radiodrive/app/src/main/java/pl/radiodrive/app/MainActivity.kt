package pl.radiodrive.app

import android.content.ComponentName
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.animation.AnimatedContent
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
import androidx.core.content.ContextCompat
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.session.MediaController
import androidx.media3.session.SessionToken
import com.google.common.util.concurrent.ListenableFuture
import pl.radiodrive.app.data.StationRepository
import pl.radiodrive.app.data.UserLibrary
import pl.radiodrive.app.model.Station
import pl.radiodrive.app.playback.RadioPlaybackService
import pl.radiodrive.app.ui.theme.RadioAmber
import pl.radiodrive.app.ui.theme.RadioCyan
import pl.radiodrive.app.ui.theme.RadioDriveTheme
import pl.radiodrive.app.ui.theme.RadioSurface2

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            RadioDriveTheme {
                val controller = rememberMediaController()
                RadioDriveApp(controller)
            }
        }
    }

    @Composable
    private fun rememberMediaController(): MediaController? {
        var controller by remember { mutableStateOf<MediaController?>(null) }
        val appContext = applicationContext

        DisposableEffect(Unit) {
            val token = SessionToken(appContext, ComponentName(appContext, RadioPlaybackService::class.java))
            val future: ListenableFuture<MediaController> = MediaController.Builder(appContext, token).buildAsync()
            future.addListener(
                { runCatching { future.get() }.onSuccess { controller = it } },
                ContextCompat.getMainExecutor(appContext),
            )
            onDispose {
                controller?.let(MediaController::release)
                if (!future.isDone) future.cancel(true)
            }
        }
        return controller
    }
}

private enum class AppTab { HOME, FAVORITES, ALL }

@Composable
private fun RadioDriveApp(controller: MediaController?) {
    val context = androidx.compose.ui.platform.LocalContext.current
    val repository = remember { StationRepository(context.applicationContext) }
    val userLibrary = remember { UserLibrary(context.applicationContext) }
    val stations = remember { repository.all() }
    val categories = remember { repository.categories() }

    var tab by rememberSaveable { mutableStateOf(AppTab.HOME) }
    var selectedCategory by rememberSaveable { mutableStateOf<String?>(null) }
    var favoriteRefresh by remember { mutableIntStateOf(0) }
    var currentMediaId by remember { mutableStateOf(controller?.currentMediaItem?.mediaId) }
    var isPlaying by remember { mutableStateOf(controller?.isPlaying == true) }

    DisposableEffect(controller) {
        if (controller == null) return@DisposableEffect onDispose { }
        val listener = object : Player.Listener {
            override fun onIsPlayingChanged(value: Boolean) { isPlaying = value }
            override fun onMediaItemTransition(mediaItem: MediaItem?, reason: Int) {
                currentMediaId = mediaItem?.mediaId
            }
        }
        controller.addListener(listener)
        currentMediaId = controller.currentMediaItem?.mediaId
        isPlaying = controller.isPlaying
        onDispose { controller.removeListener(listener) }
    }

    val currentStation = stations.firstOrNull { it.id == currentMediaId }
    val favorites = remember(favoriteRefresh) { userLibrary.favorites() }

    Scaffold(
        topBar = { RadioTopBar() },
        bottomBar = {
            NavigationBar(tonalElevation = 0.dp) {
                NavigationBarItem(
                    selected = tab == AppTab.HOME,
                    onClick = { tab = AppTab.HOME },
                    icon = { Icon(Icons.Rounded.Home, null) },
                    label = { Text("Start") },
                )
                NavigationBarItem(
                    selected = tab == AppTab.FAVORITES,
                    onClick = { tab = AppTab.FAVORITES },
                    icon = { Icon(Icons.Rounded.Favorite, null) },
                    label = { Text("Ulubione") },
                )
                NavigationBarItem(
                    selected = tab == AppTab.ALL,
                    onClick = { tab = AppTab.ALL },
                    icon = { Icon(Icons.Rounded.Radio, null) },
                    label = { Text("Stacje") },
                )
            }
        },
    ) { padding ->
        AnimatedContent(tab, label = "tab") { activeTab ->
            when (activeTab) {
                AppTab.HOME -> HomeScreen(
                    modifier = Modifier.padding(padding),
                    stations = stations,
                    categories = categories,
                    selectedCategory = selectedCategory,
                    onCategory = { selectedCategory = if (selectedCategory == it) null else it },
                    current = currentStation,
                    isPlaying = isPlaying,
                    favoriteIds = favorites,
                    onPlayPause = {
                        if (controller?.isPlaying == true) controller.pause() else controller?.play()
                    },
                    onStation = { station -> play(controller, station) },
                    onFavorite = { id -> userLibrary.toggleFavorite(id); favoriteRefresh++ },
                )
                AppTab.FAVORITES -> StationListScreen(
                    modifier = Modifier.padding(padding),
                    title = "Ulubione",
                    subtitle = "Twoje zapisane stacje",
                    stations = stations.filter { it.id in favorites },
                    currentId = currentMediaId,
                    favoriteIds = favorites,
                    onStation = { play(controller, it) },
                    onFavorite = { id -> userLibrary.toggleFavorite(id); favoriteRefresh++ },
                    searchEnabled = false,
                )
                AppTab.ALL -> StationListScreen(
                    modifier = Modifier.padding(padding),
                    title = "Wszystkie stacje",
                    subtitle = "Wybierz radio i słuchaj",
                    stations = stations,
                    currentId = currentMediaId,
                    favoriteIds = favorites,
                    onStation = { play(controller, it) },
                    onFavorite = { id -> userLibrary.toggleFavorite(id); favoriteRefresh++ },
                    searchEnabled = true,
                )
            }
        }
    }
}

private fun play(controller: MediaController?, station: Station) {
    controller ?: return
    controller.setMediaItem(station.toMediaItem())
    controller.prepare()
    controller.play()
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun RadioTopBar() {
    TopAppBar(
        title = {
            Column {
                Text("RadioDrive", fontWeight = FontWeight.Black, letterSpacing = 0.2.sp)
                Text("radio • telefon • Android Auto", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        },
        actions = {
            Surface(shape = CircleShape, color = MaterialTheme.colorScheme.surfaceVariant) {
                Icon(Icons.Rounded.DirectionsCar, null, Modifier.padding(10.dp), tint = RadioAmber)
            }
            Spacer(Modifier.width(16.dp))
        },
    )
}

@Composable
private fun HomeScreen(
    modifier: Modifier,
    stations: List<Station>,
    categories: List<String>,
    selectedCategory: String?,
    current: Station?,
    isPlaying: Boolean,
    favoriteIds: Set<String>,
    onCategory: (String) -> Unit,
    onPlayPause: () -> Unit,
    onStation: (Station) -> Unit,
    onFavorite: (String) -> Unit,
) {
    val visible = if (selectedCategory == null) stations else stations.filter { it.category == selectedCategory }
    LazyColumn(
        modifier = modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 18.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item {
            NowPlayingCard(current = current, isPlaying = isPlaying, onPlayPause = onPlayPause)
        }
        item {
            Text("Kategorie", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(10.dp))
            LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                items(categories) { category ->
                    FilterChip(
                        selected = selectedCategory == category,
                        onClick = { onCategory(category) },
                        label = { Text(category) },
                        leadingIcon = { Icon(Icons.Rounded.GraphicEq, null, Modifier.size(18.dp)) },
                    )
                }
            }
        }
        item {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text(if (selectedCategory == null) "Polecane stacje" else selectedCategory, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                    Text("Dotknij stacji, aby rozpocząć odtwarzanie", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                AssistChip(onClick = {}, label = { Text("${visible.size}") })
            }
        }
        items(visible, key = { it.id }) { station ->
            StationRow(
                station = station,
                active = current?.id == station.id,
                favorite = station.id in favoriteIds,
                onClick = { onStation(station) },
                onFavorite = { onFavorite(station.id) },
            )
        }
        item { Spacer(Modifier.height(8.dp)) }
    }
}

@Composable
private fun NowPlayingCard(current: Station?, isPlaying: Boolean, onPlayPause: () -> Unit) {
    val gradient = Brush.linearGradient(listOf(Color(0xFF342100), Color(0xFF102B2A), RadioSurface2))
    Surface(
        shape = RoundedCornerShape(30.dp),
        color = Color.Transparent,
        tonalElevation = 2.dp,
    ) {
        Column(
            Modifier
                .background(gradient)
                .padding(22.dp)
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Surface(shape = RoundedCornerShape(22.dp), color = Color.White.copy(alpha = 0.08f)) {
                    Box(Modifier.size(76.dp), contentAlignment = Alignment.Center) {
                        Icon(Icons.Rounded.Radio, null, Modifier.size(38.dp), tint = RadioAmber)
                    }
                }
                Spacer(Modifier.width(16.dp))
                Column(Modifier.weight(1f)) {
                    Text("TERAZ GRA", style = MaterialTheme.typography.labelMedium, color = RadioCyan, fontWeight = FontWeight.Bold)
                    Text(current?.name ?: "Wybierz stację", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Black, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    Text(current?.subtitle ?: "Radio internetowe gotowe do drogi", style = MaterialTheme.typography.bodyMedium, color = Color.White.copy(alpha = 0.72f), maxLines = 1, overflow = TextOverflow.Ellipsis)
                }
                FilledIconButton(
                    onClick = onPlayPause,
                    enabled = current != null,
                    modifier = Modifier.size(56.dp),
                    colors = IconButtonDefaults.filledIconButtonColors(containerColor = RadioAmber, contentColor = Color(0xFF1D1300)),
                ) {
                    Icon(if (isPlaying) Icons.Rounded.Pause else Icons.Rounded.PlayArrow, null, Modifier.size(30.dp))
                }
            }
            Spacer(Modifier.height(18.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(7.dp), verticalAlignment = Alignment.Bottom) {
                listOf(10, 18, 28, 16, 24, 12, 20, 30, 18, 12).forEachIndexed { index, height ->
                    Box(
                        Modifier
                            .width(5.dp)
                            .height(height.dp)
                            .clip(CircleShape)
                            .background(if (index % 3 == 0) RadioAmber else Color.White.copy(alpha = 0.38f))
                    )
                }
                Spacer(Modifier.weight(1f))
                Icon(Icons.Rounded.DirectionsCar, null, tint = Color.White.copy(alpha = 0.6f))
                Text("Android Auto", style = MaterialTheme.typography.labelMedium, color = Color.White.copy(alpha = 0.72f))
            }
        }
    }
}

@Composable
private fun StationListScreen(
    modifier: Modifier,
    title: String,
    subtitle: String,
    stations: List<Station>,
    currentId: String?,
    favoriteIds: Set<String>,
    onStation: (Station) -> Unit,
    onFavorite: (String) -> Unit,
    searchEnabled: Boolean,
) {
    var query by rememberSaveable { mutableStateOf("") }
    val visibleStations = if (query.isBlank()) stations else stations.filter { station ->
        station.name.contains(query, ignoreCase = true) ||
            station.subtitle.contains(query, ignoreCase = true) ||
            station.category.contains(query, ignoreCase = true)
    }

    LazyColumn(
        modifier = modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 18.dp, vertical = 16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Text(title, style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Black)
            Text(subtitle, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Spacer(Modifier.height(8.dp))
            if (searchEnabled) {
                OutlinedTextField(
                    value = query,
                    onValueChange = { query = it },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    shape = RoundedCornerShape(18.dp),
                    leadingIcon = { Icon(Icons.Rounded.Search, null) },
                    placeholder = { Text("Szukaj stacji lub kategorii") },
                )
                Spacer(Modifier.height(4.dp))
            }
        }
        if (visibleStations.isEmpty()) {
            item {
                Surface(shape = RoundedCornerShape(24.dp), color = MaterialTheme.colorScheme.surfaceVariant) {
                    Row(Modifier.padding(20.dp), verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Rounded.FavoriteBorder, null, tint = RadioAmber)
                        Spacer(Modifier.width(12.dp))
                        Text(if (searchEnabled && query.isNotBlank()) "Brak stacji pasujących do wyszukiwania." else "Tutaj pojawią się zapisane stacje.")
                    }
                }
            }
        }
        items(visibleStations, key = { it.id }) { station ->
            StationRow(
                station = station,
                active = currentId == station.id,
                favorite = station.id in favoriteIds,
                onClick = { onStation(station) },
                onFavorite = { onFavorite(station.id) },
            )
        }
    }
}

@Composable
private fun StationRow(
    station: Station,
    active: Boolean,
    favorite: Boolean,
    onClick: () -> Unit,
    onFavorite: () -> Unit,
) {
    Surface(
        modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(22.dp)).clickable(onClick = onClick),
        shape = RoundedCornerShape(22.dp),
        color = if (active) MaterialTheme.colorScheme.primary.copy(alpha = 0.10f) else MaterialTheme.colorScheme.surface,
        tonalElevation = if (active) 3.dp else 1.dp,
    ) {
        Row(Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Surface(
                shape = RoundedCornerShape(18.dp),
                color = if (active) RadioAmber else MaterialTheme.colorScheme.surfaceVariant,
            ) {
                Box(Modifier.size(58.dp), contentAlignment = Alignment.Center) {
                    Text(station.name.take(2).uppercase(), fontWeight = FontWeight.Black, color = if (active) Color(0xFF1D1300) else MaterialTheme.colorScheme.onSurface)
                }
            }
            Spacer(Modifier.width(14.dp))
            Column(Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    if (active) {
                        Icon(Icons.Rounded.GraphicEq, null, tint = RadioCyan, modifier = Modifier.size(18.dp))
                        Spacer(Modifier.width(6.dp))
                    }
                    Text(station.name, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                }
                Text(station.subtitle, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text(station.category, style = MaterialTheme.typography.labelSmall, color = RadioAmber)
            }
            IconButton(onClick = onFavorite) {
                Icon(if (favorite) Icons.Rounded.Favorite else Icons.Rounded.FavoriteBorder, null, tint = if (favorite) RadioAmber else MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}
