package pl.radiodrive.app.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

val RadioAmber = Color(0xFFFFB000)
val RadioCyan = Color(0xFF5BE7C4)
val RadioBackground = Color(0xFF090C11)
val RadioSurface = Color(0xFF121720)
val RadioSurface2 = Color(0xFF19202B)

private val DarkColors = darkColorScheme(
    primary = RadioAmber,
    secondary = RadioCyan,
    background = RadioBackground,
    surface = RadioSurface,
    surfaceVariant = RadioSurface2,
    onPrimary = Color(0xFF1D1300),
    onBackground = Color(0xFFF2F4F8),
    onSurface = Color(0xFFF2F4F8),
)

private val LightColors = lightColorScheme(
    primary = Color(0xFF865300),
    secondary = Color(0xFF006B59),
    background = Color(0xFFF7F8FA),
    surface = Color.White,
    surfaceVariant = Color(0xFFE9EDF2),
)

@Composable
fun RadioDriveTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = if (isSystemInDarkTheme()) DarkColors else LightColors,
        typography = MaterialTheme.typography,
        content = content,
    )
}
