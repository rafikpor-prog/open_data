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
import androidx.media3.session.MediaLibraryService.LibraryParams
import androidx.media3.session.MediaLibraryService.MediaLibrarySession
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
    private lateinit var userLibrary: UserLibrary

    override fun onCreate() {
        super.onCreate()
        repository = StationRepository(this)
        userLibrary = UserLibrary(this)
        player = ExoPlayer.Builder(this).build()

        player.addListener(object : Player.Listener {
            override fun onMediaItemTransition(mediaItem: MediaItem?, reason: Int) {
                mediaItem?.mediaId?.takeIf { repository.find(it) != null }?.let(userLibrary::rememberRecent)
            }
        })

        val intent = Intent(this, MainActivity::class.java)
        val pendingIntent = PendingIntent.getActivity(
            this,
            0,
            intent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )

        session = MediaLibrarySession.Builder(this, player, LibraryCallback())
            .setSessionActivity(pendingIntent)
            .build()
    }

    override fun onGetSession(controllerInfo: MediaSession.ControllerInfo): MediaLibrarySession = session

    override fun onDestroy() {
        session.release()
        player.release()
        super.onDestroy()
    }

    private inner class LibraryCallback : MediaLibrarySession.Callback {
        override fun onGetLibraryRoot(
            session: MediaLibrarySession,
            browser: MediaSession.ControllerInfo,
            params: LibraryParams?,
        ): ListenableFuture<LibraryResult<MediaItem>> =
            Futures.immediateFuture(LibraryResult.ofItem(rootItem(), params))

        override fun onGetItem(
            session: MediaLibrarySession,
            browser: MediaSession.ControllerInfo,
            mediaId: String,
        ): ListenableFuture<LibraryResult<MediaItem>> {
            val item = resolveItem(mediaId)
            return if (item != null) {
                Futures.immediateFuture(LibraryResult.ofItem(item, null))
            } else {
                Futures.immediateFuture(LibraryResult.ofError(SessionError.ERROR_BAD_VALUE))
            }
        }

        override fun onGetChildren(
            session: MediaLibrarySession,
            browser: MediaSession.ControllerInfo,
            parentId: String,
            page: Int,
            pageSize: Int,
            params: LibraryParams?,
        ): ListenableFuture<LibraryResult<ImmutableList<MediaItem>>> {
            val items = when {
                parentId == ROOT_ID -> rootChildren()
                parentId == ALL_ID -> repository.all().map(Station::toMediaItem)
                parentId == FAVORITES_ID -> userLibrary.favorites().mapNotNull(repository::find).map(Station::toMediaItem)
                parentId == RECENT_ID -> userLibrary.recent().mapNotNull(repository::find).map(Station::toMediaItem)
                parentId.startsWith(CATEGORY_PREFIX) -> {
                    val category = parentId.removePrefix(CATEGORY_PREFIX)
                    repository.inCategory(category).map(Station::toMediaItem)
                }
                else -> emptyList()
            }

            val from = (page * pageSize).coerceAtMost(items.size)
            val to = (from + pageSize).coerceAtMost(items.size)
            return Futures.immediateFuture(LibraryResult.ofItemList(items.subList(from, to), params))
        }

        override fun onAddMediaItems(
            mediaSession: MediaSession,
            controller: MediaSession.ControllerInfo,
            mediaItems: List<MediaItem>,
        ): ListenableFuture<List<MediaItem>> {
            val resolved = mediaItems.mapNotNull { requested ->
                repository.find(requested.mediaId)?.toMediaItem() ?: requested
            }
            return Futures.immediateFuture(resolved)
        }

        override fun onSearch(
            session: MediaLibrarySession,
            browser: MediaSession.ControllerInfo,
            query: String,
            params: LibraryParams?,
        ): ListenableFuture<LibraryResult<Void>> {
            val count = repository.search(query).size
            session.notifySearchResultChanged(browser, query, count, params)
            return Futures.immediateFuture(LibraryResult.ofVoid())
        }

        override fun onGetSearchResult(
            session: MediaLibrarySession,
            browser: MediaSession.ControllerInfo,
            query: String,
            page: Int,
            pageSize: Int,
            params: LibraryParams?,
        ): ListenableFuture<LibraryResult<ImmutableList<MediaItem>>> {
            val found = repository.search(query).map(Station::toMediaItem)
            val from = (page * pageSize).coerceAtMost(found.size)
            val to = (from + pageSize).coerceAtMost(found.size)
            return Futures.immediateFuture(LibraryResult.ofItemList(found.subList(from, to), params))
        }
    }

    private fun rootItem() = browsable(ROOT_ID, "RadioDrive", "Radio internetowe")

    private fun rootChildren(): List<MediaItem> = buildList {
        add(browsable(FAVORITES_ID, "Ulubione", "Twoje zapisane stacje"))
        add(browsable(RECENT_ID, "Ostatnio słuchane", "Szybki powrót do stacji"))
        add(browsable(ALL_ID, "Wszystkie stacje", "Pełna lista"))
        repository.categories().forEach { category ->
            add(browsable(CATEGORY_PREFIX + category, category, "Kategoria"))
        }
    }

    private fun resolveItem(id: String): MediaItem? = when {
        id == ROOT_ID -> rootItem()
        id == ALL_ID -> browsable(ALL_ID, "Wszystkie stacje", "Pełna lista")
        id == FAVORITES_ID -> browsable(FAVORITES_ID, "Ulubione", "Twoje zapisane stacje")
        id == RECENT_ID -> browsable(RECENT_ID, "Ostatnio słuchane", "Szybki powrót")
        id.startsWith(CATEGORY_PREFIX) -> browsable(id, id.removePrefix(CATEGORY_PREFIX), "Kategoria")
        else -> repository.find(id)?.toMediaItem()
    }

    private fun browsable(id: String, title: String, subtitle: String): MediaItem =
        MediaItem.Builder()
            .setMediaId(id)
            .setMediaMetadata(
                MediaMetadata.Builder()
                    .setTitle(title)
                    .setSubtitle(subtitle)
                    .setIsBrowsable(true)
                    .setIsPlayable(false)
                    .build()
            )
            .build()

    companion object {
        private const val ROOT_ID = "root"
        private const val ALL_ID = "all"
        private const val FAVORITES_ID = "favorites"
        private const val RECENT_ID = "recent"
        private const val CATEGORY_PREFIX = "category:"
    }
}
