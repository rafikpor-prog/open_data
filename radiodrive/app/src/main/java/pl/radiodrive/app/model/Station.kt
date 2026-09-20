package pl.radiodrive.app.model

import android.net.Uri
import androidx.media3.common.MediaItem
import androidx.media3.common.MediaMetadata

data class Station(
    val id: String,
    val name: String,
    val streamUrl: String,
    val logoUrl: String? = null,
    val homepage: String? = null,
    val category: String = "Różne",
    val state: String = "",
    val tags: List<String> = emptyList(),
    val codec: String = "",
    val bitrate: Int = 0,
    val hls: Boolean = false,
    val votes: Int = 0,
    val lastCheckOk: Boolean = true,
    val lastCheckTime: String = "",
) {
    val subtitle: String
        get() = buildList {
            if (state.isNotBlank()) add(state)
            if (category.isNotBlank()) add(category)
            if (bitrate > 0) add("$bitrate kb/s")
        }.joinToString(" • ")

    val streamQuality: String
        get() = when {
            bitrate >= 256 -> "Bardzo wysoka"
            bitrate >= 160 -> "Wysoka"
            bitrate >= 96 -> "Standard"
            bitrate > 0 -> "Oszczędna"
            else -> "Auto"
        }

    fun toMediaItem(): MediaItem {
        val metadata = MediaMetadata.Builder()
            .setTitle(name)
            .setArtist(category)
            .setAlbumTitle(state.ifBlank { "Polska" })
            .setIsBrowsable(false)
            .setIsPlayable(true)
            .apply { logoUrl?.let { runCatching { setArtworkUri(Uri.parse(it)) } } }
            .build()

        return MediaItem.Builder()
            .setMediaId(id)
            .setUri(streamUrl)
            .setMediaMetadata(metadata)
            .build()
    }
}
