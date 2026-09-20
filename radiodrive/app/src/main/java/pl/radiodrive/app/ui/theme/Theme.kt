package pl.radiodrive.app.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

val RadioAmber = Color(0xFFFFB21D)
val RadioCyan = Color(0xFF16D7FF)
val RadioBackground = Color(0xFF050B12)
val RadioSurface = Color(0xFF0B1520)
val RadioSurface2 = Color(0xFF101F2E)

private val DriveColors = darkColorScheme(
    primary = RadioCyan,
    secondary = RadioAmber,
    tertiary = Color(0xFF5BE7C4),
    background = RadioBackground,
    surface = RadioSurface,
    surfaceVariant = RadioSurface2,
    onPrimary = Color(0xFF001F29),
    onSecondary = Color(0xFF271800),
    onBackground = Color(0xFFF3F8FC),
    onSurface = Color(0xFFF3F8FC),
    onSurfaceVariant = Color(0xFF9EB1C2),
)

@Composable
fun RadioDriveTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = DriveColors,
        typography = MaterialTheme.typography,
        content = content,
    )
}
