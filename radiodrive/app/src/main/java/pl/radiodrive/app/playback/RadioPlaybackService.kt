package pl.radiodrive.app.playback

import android.app.PendingIntent
import android.content.Intent
import androidx.media3.common.MediaItem
import androidx.media3.common.MediaMetadata
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.session.LibraryResult
import androidx.media3.session.MediaLibraryService
import androidx.media3.session.MediaSession
import androidx.media3.session.SessionError
import com.google.common.collect.ImmutableList
import com.google.common.util.concurrent.Futures
import com.google.common.util.concurrent.ListenableFuture
import pl.radiodrive.app.MainActivity
import pl.radiodrive.app.data.StationRepository
import pl.radiodrive.app.data.UserLibrary
import pl.radiodrive.app.model.Station

class RadioPlaybackService : MediaLibraryService() {

    private lateinit var player: ExoPlayer
    private lateinit var session: MediaLibrarySession
    private lateinit var repository: StationRepository
    private lateinit var library: UserLibrary

    override fun onCreate() {
        super.onCreate()
        repository = StationRepository.get(this)
        library = UserLibrary(this)
        player = ExoPlayer.Builder(this).build()
        player.addListener(object : Player.Listener {
            override fun onMediaItemTransition(mediaItem: MediaItem?, reason: Int) {
                mediaItem?.mediaId?.takeIf { it.isNotBlank() }?.let(library::rememberRecent)
            }
        })

        val pending = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )
        session = MediaLibrarySession.Builder(this, player, Callback())
            .setSessionActivity(pending)
            .build()
    }

    override fun onGetSession(controllerInfo: MediaSession.ControllerInfo): MediaLibrarySession = session

    override fun onDestroy() {
        session.release()
        player.release()
        super.onDestroy()
    }

    private inner class Callback : MediaLibrarySession.Callback {
        override fun onGetLibraryRoot(
            session: MediaLibrarySession,
            browser: MediaSession.ControllerInfo,
            params: LibraryParams?
        ): ListenableFuture<LibraryResult<MediaItem>> =
            Futures.immediateFuture(LibraryResult.ofItem(browsable(ROOT, "RadioDrive Polska", "Aktywne polskie stacje"), params))

        override fun onGetChildren(
            session: MediaLibrarySession,
            browser: MediaSession.ControllerInfo,
            parentId: String,
            page: Int,
            pageSize: Int,
            params: LibraryParams?
        ): ListenableFuture<LibraryResult<ImmutableList<MediaItem>>> {
            val all = repository.all()
            val items = when {
                parentId == ROOT -> buildList {
                    add(browsable(FAVORITES, "Ulubione", "Twoje zapisane stacje"))
                    add(browsable(RECENT, "Ostatnio słuchane", "Historia odtwarzania"))
                    add(browsable(ALL, "Wszystkie polskie stacje", "${all.size} aktywnych pozycji"))
                    repository.categories().forEach { add(browsable("cat:$it", it, "Kategoria")) }
                }
                parentId == ALL -> all.map(Station::toMediaItem)
                parentId == FAVORITES -> library.favorites().mapNotNull(repository::find).map(Station::toMediaItem)
                parentId == RECENT -> library.recent().mapNotNull(repository::find).map(Station::toMediaItem)
                parentId.startsWith("cat:") -> all.filter { it.category == parentId.removePrefix("cat:") }.map(Station::toMediaItem)
                else -> emptyList()
            }
            val from = (page * pageSize).coerceAtMost(items.size)
            val to = (from + pageSize).coerceAtMost(items.size)
            return Futures.immediateFuture(LibraryResult.ofItemList(items.subList(from, to), params))
        }

        override fun onGetItem(
            session: MediaLibrarySession,
            browser: MediaSession.ControllerInfo,
            mediaId: String
        ): ListenableFuture<LibraryResult<MediaItem>> {
            val item = repository.find(mediaId)?.toMediaItem()
            return if (item != null) Futures.immediateFuture(LibraryResult.ofItem(item, null))
            else Futures.immediateFuture(LibraryResult.ofError(SessionError.ERROR_BAD_VALUE))
        }

        override fun onSearch(
            session: MediaLibrarySession,
            browser: MediaSession.ControllerInfo,
            query: String,
            params: LibraryParams?
        ): ListenableFuture<LibraryResult<Void>> {
            val count = search(query).size
            session.notifySearchResultChanged(browser, query, count, params)
            return Futures.immediateFuture(LibraryResult.ofVoid())
        }

        override fun onGetSearchResult(
            session: MediaLibrarySession,
            browser: MediaSession.ControllerInfo,
            query: String,
            page: Int,
            pageSize: Int,
            params: LibraryParams?
        ): ListenableFuture<LibraryResult<ImmutableList<MediaItem>>> {
            val found = search(query).map(Station::toMediaItem)
            val from = (page * pageSize).coerceAtMost(found.size)
            val to = (from + pageSize).coerceAtMost(found.size)
            return Futures.immediateFuture(LibraryResult.ofItemList(found.subList(from, to), params))
        }

        override fun onAddMediaItems(
            mediaSession: MediaSession,
            controller: MediaSession.ControllerInfo,
            mediaItems: List<MediaItem>
        ): ListenableFuture<List<MediaItem>> =
            Futures.immediateFuture(mediaItems.map { repository.find(it.mediaId)?.toMediaItem() ?: it })
    }

    private fun search(q: String): List<Station> {
        val query = q.trim()
        if (query.isBlank()) return emptyList()
        return repository.all().filter {
            it.name.contains(query, true) ||
                it.state.contains(query, true) ||
                it.category.contains(query, true) ||
                it.tags.any { tag -> tag.contains(query, true) }
        }
    }

    private fun browsable(id: String, title: String, subtitle: String) =
        MediaItem.Builder()
            .setMediaId(id)
            .setMediaMetadata(
                MediaMetadata.Builder()
                    .setTitle(title)
                    .setSubtitle(subtitle)
                    .setIsBrowsable(true)
                    .setIsPlayable(false)
                    .build()
            ).build()

    companion object {
        private const val ROOT = "root"
        private const val ALL = "all"
        private const val FAVORITES = "favorites"
        private const val RECENT = "recent"
    }
}
