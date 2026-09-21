package pl.radiodrive.app.car

import android.content.ComponentName
import android.content.Intent
import android.support.v4.media.MediaBrowserCompat
import android.support.v4.media.MediaMetadataCompat
import android.support.v4.media.session.MediaControllerCompat
import androidx.car.app.CarAppService
import androidx.car.app.CarContext
import androidx.car.app.annotations.ExperimentalCarApi
import androidx.car.app.Screen
import androidx.car.app.Session
import androidx.car.app.SessionInfo
import androidx.car.app.media.MediaPlaybackManager
import androidx.car.app.media.model.MediaPlaybackTemplate
import androidx.car.app.model.Action
import androidx.car.app.model.Header
import androidx.car.app.model.ItemList
import androidx.car.app.model.ListTemplate
import androidx.car.app.model.Row
import androidx.car.app.model.Template
import androidx.car.app.validation.HostValidator
import androidx.lifecycle.DefaultLifecycleObserver
import androidx.lifecycle.LifecycleOwner
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch
import pl.radiodrive.app.alerts.AlertSource
import pl.radiodrive.app.alerts.SafetyAlertsRepository
import pl.radiodrive.app.data.StationRepository
import pl.radiodrive.app.data.UserLibrary
import pl.radiodrive.app.playback.LegacyAutoMediaService
import pl.radiodrive.app.road.RoadAssistStore
import pl.radiodrive.app.weather.WeatherRepository
import java.util.Locale
import java.util.concurrent.CopyOnWriteArraySet

class RadioDriveCarAppService : CarAppService() {
    override fun createHostValidator(): HostValidator =
        HostValidator.Builder(this)
            .addAllowedHosts(androidx.car.app.R.array.hosts_allowlist_sample)
            .build()

    override fun onCreateSession(sessionInfo: SessionInfo): Session =
        RadioDriveCarSession()
}

private class RadioDriveCarSession : Session() {
    private var browser: MediaBrowserCompat? = null
    private var controller: MediaControllerCompat? = null
    private var pendingStationId: String? = null
    private val listeners = CopyOnWriteArraySet<() -> Unit>()

    private val controllerCallback = object : MediaControllerCompat.Callback() {
        override fun onMetadataChanged(metadata: MediaMetadataCompat?) = notifyChanged()
        override fun onPlaybackStateChanged(state: android.support.v4.media.session.PlaybackStateCompat?) = notifyChanged()
    }

    init {
        lifecycle.addObserver(object : DefaultLifecycleObserver {
            override fun onDestroy(owner: LifecycleOwner) {
                controller?.unregisterCallback(controllerCallback)
                browser?.disconnect()
                listeners.clear()
            }
        })
    }

    override fun onCreateScreen(intent: Intent): Screen {
        ensureMediaConnection()
        return RadioDriveDashboardScreen(carContext, this)
    }

    fun addListener(listener: () -> Unit) {
        listeners += listener
    }

    fun removeListener(listener: () -> Unit) {
        listeners -= listener
    }

    fun metadata(): MediaMetadataCompat? = controller?.metadata

    fun currentStationId(): String? =
        controller?.metadata?.getString(MediaMetadataCompat.METADATA_KEY_MEDIA_ID)

    fun playStation(id: String) {
        val active = controller
        if (active == null) {
            pendingStationId = id
            ensureMediaConnection()
        } else {
            active.transportControls.playFromMediaId(id, null)
        }
    }

    fun openPlayback(screen: Screen) {
        screen.screenManager.push(RadioDrivePlaybackScreen(carContext))
    }

    private fun ensureMediaConnection() {
        if (browser != null) return
        val connection = object : MediaBrowserCompat.ConnectionCallback() {
            override fun onConnected() {
                val mediaBrowser = browser ?: return
                val mediaController = MediaControllerCompat(carContext, mediaBrowser.sessionToken)
                controller = mediaController
                mediaController.registerCallback(controllerCallback)

                runCatching {
                    val playbackManager =
                        carContext.getCarService(CarContext.MEDIA_PLAYBACK_SERVICE) as MediaPlaybackManager
                    playbackManager.registerMediaPlaybackToken(mediaBrowser.sessionToken)
                }

                pendingStationId?.let {
                    pendingStationId = null
                    mediaController.transportControls.playFromMediaId(it, null)
                }
                notifyChanged()
            }

            override fun onConnectionSuspended() = notifyChanged()
            override fun onConnectionFailed() = notifyChanged()
        }

        browser = MediaBrowserCompat(
            carContext,
            ComponentName(carContext, LegacyAutoMediaService::class.java),
            connection,
            null
        ).also { it.connect() }
    }

    private fun notifyChanged() {
        listeners.forEach { listener -> runCatching { listener() } }
    }
}

private class RadioDriveDashboardScreen(
    carContext: CarContext,
    private val session: RadioDriveCarSession,
) : Screen(carContext) {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
    private val repository = StationRepository.get(carContext.applicationContext)
    private val library = UserLibrary(carContext.applicationContext)
    private val weather = WeatherRepository.get(carContext.applicationContext)
    private val alerts = SafetyAlertsRepository.get(carContext.applicationContext)
    private val sessionListener: () -> Unit = { invalidate() }

    init {
        session.addListener(sessionListener)
        weather.refresh()
        alerts.refresh()

        scope.launch { weather.state.collectLatest { invalidate() } }
        scope.launch { alerts.state.collectLatest { invalidate() } }
        scope.launch { RoadAssistStore.state.collectLatest { invalidate() } }

        lifecycle.addObserver(object : DefaultLifecycleObserver {
            override fun onDestroy(owner: LifecycleOwner) {
                session.removeListener(sessionListener)
                scope.cancel()
            }
        })
    }

    @OptIn(ExperimentalCarApi::class)
    override fun onGetTemplate(): Template {
        val metadata = session.metadata()
        val stationId = session.currentStationId()
        val station = stationId?.let(repository::find)
        val streamed = metadata
            ?.getString(MediaMetadataCompat.METADATA_KEY_ARTIST)
            .orEmpty()
            .takeIf { it.isNotBlank() }

        val weatherData = weather.state.value.data
        val weatherText = weatherData?.let {
            val temp = if (it.temperature.isNaN()) "—" else String.format(Locale.US, "%.0f°C", it.temperature)
            "$temp • ${it.description} • ${it.place}"
        } ?: weather.state.value.error ?: "Pogoda oczekuje na lokalizację telefonu"

        val navigation = RoadAssistStore.state.value.googleMapsInstruction
        val navText = navigation?.let { "${navigationArrow(it)} $it" }
            ?: "↑ Uruchom prowadzenie w Google Maps. Wskazówka pojawi się tutaj."

        val alert = alerts.state.value.alerts
            .sortedWith(
                compareBy(
                    { when (it.source) {
                        AlertSource.RCB -> 0
                        AlertSource.ROAD -> 1
                        AlertSource.RSO -> 2
                    } },
                    { it.distanceKm ?: Int.MAX_VALUE }
                )
            )
            .firstOrNull()

        val alertText = alert?.let {
            val prefix = when (it.source) {
                AlertSource.RCB -> "RCB"
                AlertSource.RSO -> "RSO"
                AlertSource.ROAD -> "DROGA"
            }
            val distance = it.distanceKm?.let { km -> " • $km km" }.orEmpty()
            "$prefix$distance • ${it.title}${if (it.body.isNotBlank()) " • ${it.body}" else ""}"
        } ?: "Brak aktywnych komunikatów dla bieżącej lokalizacji"

        val favorites = library.favorites().mapNotNull(repository::find)

        val mediaAction = Action.Builder(Action.MEDIA_PLAYBACK)
            .setOnClickListener { session.openPlayback(this) }
            .build()

        val list = ItemList.Builder()
            .addItem(
                Row.Builder()
                    .setTitle("TERAZ GRA")
                    .addText(station?.name ?: "Wybierz stację w RadioDrive")
                    .addText(streamed ?: station?.subtitle.orEmpty().ifBlank { "Radio internetowe" })
                    .setOnClickListener { session.openPlayback(this) }
                    .addAction(mediaAction)
                    .build()
            )
            .addItem(
                Row.Builder()
                    .setTitle("POGODA")
                    .addText(weatherText)
                    .setOnClickListener { weather.refresh() }
                    .build()
            )
            .addItem(
                Row.Builder()
                    .setTitle("NAWIGACJA")
                    .addText(navText)
                    .build()
            )
            .addItem(
                Row.Builder()
                    .setTitle("KOMUNIKAT")
                    .addText(alertText.take(220))
                    .setOnClickListener { alerts.refresh() }
                    .build()
            )
            .addItem(
                Row.Builder()
                    .setTitle("ULUBIONE")
                    .addText(
                        if (favorites.isEmpty()) "Brak ulubionych stacji"
                        else favorites.take(4).joinToString(" • ") { it.name }
                    )
                    .setBrowsable(true)
                    .setOnClickListener {
                        screenManager.push(RadioDriveFavoritesScreen(carContext, session))
                    }
                    .build()
            )
            .build()

        return ListTemplate.Builder()
            .setSingleList(list)
            .setHeader(
                Header.Builder()
                    .setTitle("RadioDrive • Odtwarzanie i trasa")
                    .setStartHeaderAction(Action.APP_ICON)
                    .build()
            )
            .addAction(mediaAction)
            .build()
    }
}

private class RadioDriveFavoritesScreen(
    carContext: CarContext,
    private val session: RadioDriveCarSession,
) : Screen(carContext) {
    private val repository = StationRepository.get(carContext.applicationContext)
    private val library = UserLibrary(carContext.applicationContext)

    @OptIn(ExperimentalCarApi::class)
    override fun onGetTemplate(): Template {
        val currentId = session.currentStationId()
        val favorites = library.favorites().mapNotNull(repository::find)

        val listBuilder = ItemList.Builder()
        if (favorites.isEmpty()) {
            listBuilder.addItem(
                Row.Builder()
                    .setTitle("Brak ulubionych")
                    .addText("Dodaj stacje do ulubionych w telefonie lub tablecie.")
                    .build()
            )
        } else {
            favorites.take(40).forEach { station ->
                val row = Row.Builder()
                    .setTitle(station.name)
                    .addText(
                        buildString {
                            append(station.category)
                            if (station.state.isNotBlank()) append(" • ").append(station.state)
                            if (station.bitrate > 0) append(" • ").append(station.bitrate).append(" kb/s")
                        }
                    )
                    .setOnClickListener { session.playStation(station.id) }

                if (station.id == currentId) {
                    row.addAction(
                        Action.Builder(Action.MEDIA_PLAYBACK)
                            .setOnClickListener { session.openPlayback(this) }
                            .build()
                    )
                }
                listBuilder.addItem(row.build())
            }
        }

        return ListTemplate.Builder()
            .setSingleList(listBuilder.build())
            .setHeader(
                Header.Builder()
                    .setTitle("Ulubione stacje")
                    .setStartHeaderAction(Action.BACK)
                    .build()
            )
            .build()
    }
}

private class RadioDrivePlaybackScreen(
    carContext: CarContext,
) : Screen(carContext) {
    @OptIn(ExperimentalCarApi::class)
    override fun onGetTemplate(): Template =
        MediaPlaybackTemplate.Builder()
            .setHeader(
                Header.Builder()
                    .setTitle("RadioDrive")
                    .setStartHeaderAction(Action.BACK)
                    .build()
            )
            .build()
}

private fun navigationArrow(text: String): String {
    val value = text.lowercase(Locale.ROOT)
    return when {
        "zawró" in value || "u-turn" in value -> "↶"
        "rondo" in value || "roundabout" in value -> "⟳"
        "w lewo" in value || "left" in value -> "↰"
        "w prawo" in value || "right" in value -> "↱"
        "zjazd" in value || "exit" in value -> "↗"
        else -> "↑"
    }
}
