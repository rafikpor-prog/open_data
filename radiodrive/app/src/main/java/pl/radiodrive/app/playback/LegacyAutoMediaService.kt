package pl.radiodrive.app.playback

import android.content.ComponentName
import android.net.Uri
import android.os.Bundle
import android.support.v4.media.MediaBrowserCompat
import android.support.v4.media.MediaDescriptionCompat
import android.support.v4.media.MediaMetadataCompat
import android.support.v4.media.session.MediaSessionCompat
import android.support.v4.media.session.PlaybackStateCompat
import androidx.core.content.ContextCompat
import androidx.media.MediaBrowserServiceCompat
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.session.MediaController
import androidx.media3.session.SessionToken
import com.google.common.util.concurrent.ListenableFuture
import pl.radiodrive.app.data.StationRepository
import pl.radiodrive.app.model.Station

/**
 * Compatibility bridge for Android Auto head units that still discover
 * MediaBrowserServiceCompat more reliably than Media3 MediaLibraryService.
 *
 * Playback remains owned by RadioPlaybackService / Media3. This service only
 * exposes the browse tree and forwards car controls to the same Media3 session.
 */
class LegacyAutoMediaService : MediaBrowserServiceCompat() {

    private lateinit var repository: StationRepository
    private lateinit var compatSession: MediaSessionCompat
    private var controller: MediaController? = null
    private var controllerFuture: ListenableFuture<MediaController>? = null

    override fun onCreate() {
        super.onCreate()
        repository = StationRepository.get(this)

        compatSession = MediaSessionCompat(this, "RadioDriveAuto").apply {
            setCallback(object : MediaSessionCompat.Callback() {
                override fun onPlayFromMediaId(mediaId: String?, extras: Bundle?) {
                    mediaId?.let(::playStation)
                }

                override fun onPlayFromSearch(query: String?, extras: Bundle?) {
                    val station = query
                        ?.takeIf { it.isNotBlank() }
                        ?.let { q ->
                            repository.all().firstOrNull {
                                it.name.contains(q, true) ||
                                    it.category.contains(q, true) ||
                                    it.state.contains(q, true)
                            }
                        }
                    station?.let { playStation(it.id) }
                }

                override fun onPlay() {
                    controller?.play()
                }

                override fun onPause() {
                    controller?.pause()
                }

                override fun onStop() {
                    controller?.stop()
                }
            })
            isActive = true
        }
        sessionToken = compatSession.sessionToken

        val token = SessionToken(this, ComponentName(this, RadioPlaybackService::class.java))
        val future = MediaController.Builder(this, token).buildAsync()
        controllerFuture = future
        future.addListener(
            {
                runCatching { future.get() }.onSuccess { mediaController ->
                    controller = mediaController
                    mediaController.addListener(object : Player.Listener {
                        override fun onIsPlayingChanged(isPlaying: Boolean) = syncSession()
                        override fun onPlaybackStateChanged(playbackState: Int) = syncSession()
                        override fun onMediaItemTransition(mediaItem: MediaItem?, reason: Int) = syncSession()
                        override fun onMediaMetadataChanged(mediaMetadata: androidx.media3.common.MediaMetadata) = syncSession()
                    })
                    syncSession()
                }
            },
            ContextCompat.getMainExecutor(this)
        )
    }

    override fun onDestroy() {
        controller?.let(MediaController::release)
        controllerFuture?.takeIf { !it.isDone }?.cancel(true)
        compatSession.release()
        super.onDestroy()
    }

    override fun onGetRoot(
        clientPackageName: String,
        clientUid: Int,
        rootHints: Bundle?
    ): BrowserRoot = BrowserRoot(
        ROOT,
        Bundle().apply {
            putBoolean("android.media.browse.CONTENT_STYLE_SUPPORTED", true)
            putInt("android.media.browse.CONTENT_STYLE_BROWSABLE_HINT", 2)
            putInt("android.media.browse.CONTENT_STYLE_PLAYABLE_HINT", 2)
        }
    )

    override fun onLoadChildren(
        parentId: String,
        result: Result<MutableList<MediaBrowserCompat.MediaItem>>
    ) {
        result.sendResult(children(parentId).toMutableList())
    }

    override fun onSearch(
        query: String,
        extras: Bundle?,
        result: Result<MutableList<MediaBrowserCompat.MediaItem>>
    ) {
        val q = query.trim()
        val found = if (q.isBlank()) emptyList() else repository.all().filter { station ->
            station.name.contains(q, true) ||
                station.category.contains(q, true) ||
                station.state.contains(q, true) ||
                station.tags.any { it.contains(q, true) }
        }
        result.sendResult(found.map(::playable).toMutableList())
    }

    private fun children(parentId: String): List<MediaBrowserCompat.MediaItem> {
        val all = repository.all()
        return when {
            parentId == ROOT -> buildList {
                add(folder(FAVORITES, "Ulubione", "Twoje zapisane stacje"))
                add(folder(RECENT, "Ostatnio słuchane", "Ostatnio odtwarzane stacje"))
                add(folder(ALL, "Wszystkie polskie stacje", "${all.size} aktywnych pozycji"))
                repository.categories().forEach { category ->
                    add(folder("cat:$category", category, "Kategoria"))
                }
            }
            parentId == ALL -> all.map(::playable)
            parentId == FAVORITES -> {
                val favorites = getSharedPreferences("radio_library", MODE_PRIVATE)
                    .getStringSet("favorites", emptySet()).orEmpty()
                all.filter { it.id in favorites }.map(::playable)
            }
            parentId == RECENT -> {
                val recent = getSharedPreferences("radio_library", MODE_PRIVATE)
                    .getString("recent", "").orEmpty()
                    .split('|')
                    .filter { it.isNotBlank() }
                recent.mapNotNull { id -> repository.find(id) }.map(::playable)
            }
            parentId.startsWith("cat:") ->
                all.filter { it.category == parentId.removePrefix("cat:") }.map(::playable)
            else -> emptyList()
        }
    }

    private fun folder(
        id: String,
        title: String,
        subtitle: String
    ): MediaBrowserCompat.MediaItem =
        MediaBrowserCompat.MediaItem(
            MediaDescriptionCompat.Builder()
                .setMediaId(id)
                .setTitle(title)
                .setSubtitle(subtitle)
                .build(),
            MediaBrowserCompat.MediaItem.FLAG_BROWSABLE
        )

    private fun playable(station: Station): MediaBrowserCompat.MediaItem =
        MediaBrowserCompat.MediaItem(
            MediaDescriptionCompat.Builder()
                .setMediaId(station.id)
                .setTitle(station.name)
                .setSubtitle(station.subtitle.ifBlank { station.category })
                .apply { station.logoUrl?.let { setIconUri(Uri.parse(it)) } }
                .build(),
            MediaBrowserCompat.MediaItem.FLAG_PLAYABLE
        )

    private fun playStation(id: String) {
        val station = repository.find(id) ?: return
        controller?.let { mediaController ->
            mediaController.setMediaItem(station.toMediaItem())
            mediaController.prepare()
            mediaController.play()
        }
    }

    private fun syncSession() {
        val mediaController = controller ?: return
        val state = when {
            mediaController.playbackState == Player.STATE_BUFFERING -> PlaybackStateCompat.STATE_BUFFERING
            mediaController.isPlaying -> PlaybackStateCompat.STATE_PLAYING
            mediaController.playbackState == Player.STATE_IDLE -> PlaybackStateCompat.STATE_STOPPED
            else -> PlaybackStateCompat.STATE_PAUSED
        }

        compatSession.setPlaybackState(
            PlaybackStateCompat.Builder()
                .setActions(
                    PlaybackStateCompat.ACTION_PLAY or
                        PlaybackStateCompat.ACTION_PAUSE or
                        PlaybackStateCompat.ACTION_PLAY_PAUSE or
                        PlaybackStateCompat.ACTION_STOP or
                        PlaybackStateCompat.ACTION_PLAY_FROM_MEDIA_ID or
                        PlaybackStateCompat.ACTION_PLAY_FROM_SEARCH
                )
                .setState(
                    state,
                    PlaybackStateCompat.PLAYBACK_POSITION_UNKNOWN,
                    if (mediaController.isPlaying) 1f else 0f
                )
                .build()
        )

        val station = repository.find(mediaController.currentMediaItem?.mediaId.orEmpty()) ?: return
        val streamedTitle = mediaController.mediaMetadata.title?.toString()
            ?.takeIf { it.isNotBlank() && !it.equals(station.name, true) }
        val streamedArtist = mediaController.mediaMetadata.artist?.toString()
            ?.takeIf { it.isNotBlank() && !it.equals(station.category, true) }

        compatSession.setMetadata(
            MediaMetadataCompat.Builder()
                .putString(MediaMetadataCompat.METADATA_KEY_MEDIA_ID, station.id)
                .putString(MediaMetadataCompat.METADATA_KEY_TITLE, station.name)
                .putString(
                    MediaMetadataCompat.METADATA_KEY_ARTIST,
                    listOfNotNull(streamedArtist, streamedTitle)
                        .joinToString(" — ")
                        .ifBlank { station.category }
                )
                .putString(MediaMetadataCompat.METADATA_KEY_ALBUM, station.state.ifBlank { "Polska" })
                .apply {
                    station.logoUrl?.let {
                        putString(MediaMetadataCompat.METADATA_KEY_ART_URI, it)
                        putString(MediaMetadataCompat.METADATA_KEY_DISPLAY_ICON_URI, it)
                    }
                }
                .build()
        )
    }

    companion object {
        private const val ROOT = "root"
        private const val ALL = "all"
        private const val FAVORITES = "favorites"
        private const val RECENT = "recent"
    }
}
