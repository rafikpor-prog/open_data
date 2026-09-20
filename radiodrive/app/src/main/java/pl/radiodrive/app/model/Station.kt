package pl.radiodrive.app.model

import android.net.Uri
import androidx.media3.common.MediaItem
import androidx.media3.common.MediaMetadata

/** Single live radio station. */
data class Station(
    val id: String,
    val name: String,
    val subtitle: String,
    val streamUrl: String,
    val category: String,
    val logoUrl: String? = null,
) {
    fun toMediaItem(): MediaItem {
        val metadata = MediaMetadata.Builder()
            .setTitle(name)
            .setArtist(subtitle)
            .setAlbumTitle(category)
            .setIsBrowsable(false)
            .setIsPlayable(true)
            .apply { logoUrl?.let { setArtworkUri(Uri.parse(it)) } }
            .build()

        return MediaItem.Builder()
            .setMediaId(id)
            .setUri(streamUrl)
            .setMediaMetadata(metadata)
            .build()
    }
}
