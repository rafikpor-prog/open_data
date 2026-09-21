package pl.radiodrive.app.weather

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Air
import androidx.compose.material.icons.rounded.Cloud
import androidx.compose.material.icons.rounded.LocationOn
import androidx.compose.material.icons.rounded.Refresh
import androidx.compose.material.icons.rounded.WaterDrop
import androidx.compose.material.icons.rounded.WbSunny
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import pl.radiodrive.app.ui.theme.RadioAmber
import pl.radiodrive.app.ui.theme.RadioCyan
import java.util.Locale

@Composable
fun WeatherPanel() {
    val context = LocalContext.current
    val repository = remember { WeatherRepository.get(context.applicationContext) }
    val state by repository.state.collectAsStateWithLifecycle()
    var permissionGranted by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION) ==
                PackageManager.PERMISSION_GRANTED
        )
    }

    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        permissionGranted = granted
        if (granted) repository.refresh()
    }

    LaunchedEffect(permissionGranted) {
        if (permissionGranted && state.data == null && !state.loading) repository.refresh()
    }

    Surface(
        shape = RoundedCornerShape(26.dp),
        color = MaterialTheme.colorScheme.surfaceVariant,
        tonalElevation = 1.dp
    ) {
        Column(Modifier.fillMaxWidth().padding(18.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Surface(shape = CircleShape, color = RadioCyan.copy(alpha = .14f)) {
                    Icon(
                        if ((state.data?.weatherCode ?: 3) <= 1) Icons.Rounded.WbSunny else Icons.Rounded.Cloud,
                        contentDescription = null,
                        modifier = Modifier.padding(10.dp),
                        tint = if ((state.data?.weatherCode ?: 3) <= 1) RadioAmber else RadioCyan
                    )
                }
                Spacer(Modifier.width(12.dp))
                Column(Modifier.weight(1f)) {
                    Text("Pogoda w trasie", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Black)
                    Text(
                        state.data?.place ?: "Na podstawie przybliżonej lokalizacji telefonu",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                if (permissionGranted) {
                    IconButton(onClick = repository::refresh, enabled = !state.loading) {
                        if (state.loading) CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp)
                        else Icon(Icons.Rounded.Refresh, "Odśwież pogodę")
                    }
                }
            }

            Spacer(Modifier.height(14.dp))

            if (!permissionGranted) {
                Text(
                    "RadioDrive używa lokalizacji wyłącznie do lokalnej pogody. Wystarczy dostęp przybliżony.",
                    style = MaterialTheme.typography.bodyMedium
                )
                Spacer(Modifier.height(12.dp))
                Button(onClick = { permissionLauncher.launch(Manifest.permission.ACCESS_COARSE_LOCATION) }) {
                    Icon(Icons.Rounded.LocationOn, null)
                    Spacer(Modifier.width(8.dp))
                    Text("Włącz pogodę dla mojej lokalizacji")
                }
            } else {
                state.data?.let { weather ->
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            if (weather.temperature.isNaN()) "—°" else "${String.format(Locale.US, "%.0f", weather.temperature)}°",
                            style = MaterialTheme.typography.displaySmall,
                            fontWeight = FontWeight.Black
                        )
                        Spacer(Modifier.width(14.dp))
                        Column {
                            Text(weather.description, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                            if (!weather.apparentTemperature.isNaN()) {
                                Text(
                                    "Odczuwalna ${String.format(Locale.US, "%.0f", weather.apparentTemperature)}°C",
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        }
                    }

                    Spacer(Modifier.height(14.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        if (weather.humidity >= 0) WeatherMetric(Icons.Rounded.WaterDrop, "Wilgotność", "${weather.humidity}%")
                        if (!weather.windSpeed.isNaN()) WeatherMetric(Icons.Rounded.Air, "Wiatr", "${String.format(Locale.US, "%.0f", weather.windSpeed)} km/h")
                    }

                    Spacer(Modifier.height(8.dp))
                    val range = if (weather.minTemperature != null && weather.maxTemperature != null) {
                        "Dziś ${String.format(Locale.US, "%.0f", weather.minTemperature)}° / ${String.format(Locale.US, "%.0f", weather.maxTemperature)}°"
                    } else "Prognoza dzienna niedostępna"
                    val rain = weather.precipitationProbability?.let { " • opady maks. $it%" }.orEmpty()
                    Text(range + rain, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }

                state.error?.let {
                    if (state.data != null) Spacer(Modifier.height(8.dp))
                    Text(it, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.error)
                }
            }
        }
    }
}

@Composable
private fun WeatherMetric(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    label: String,
    value: String,
) {
    Surface(shape = RoundedCornerShape(16.dp), color = MaterialTheme.colorScheme.surface) {
        Row(Modifier.padding(horizontal = 12.dp, vertical = 9.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(icon, null, Modifier.size(18.dp), tint = RadioCyan)
            Spacer(Modifier.width(7.dp))
            Column {
                Text(label, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Text(value, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Bold)
            }
        }
    }
}


@Composable
fun CompactWeatherInline() {
    val context = LocalContext.current
    val repository = remember { WeatherRepository.get(context.applicationContext) }
    val state by repository.state.collectAsStateWithLifecycle()
    var permissionGranted by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION) ==
                PackageManager.PERMISSION_GRANTED
        )
    }

    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        permissionGranted = granted
        if (granted) repository.refresh()
    }

    LaunchedEffect(permissionGranted) {
        if (permissionGranted && state.data == null && !state.loading) repository.refresh()
    }

    Column(Modifier.fillMaxWidth()) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(
                if ((state.data?.weatherCode ?: 3) <= 1) Icons.Rounded.WbSunny else Icons.Rounded.Cloud,
                null,
                tint = if ((state.data?.weatherCode ?: 3) <= 1) RadioAmber else RadioCyan,
                modifier = Modifier.size(22.dp)
            )
            Spacer(Modifier.width(8.dp))
            Text(
                "POGODA W TRASIE",
                style = MaterialTheme.typography.labelSmall,
                fontWeight = FontWeight.Black,
                color = RadioCyan
            )
            Spacer(Modifier.weight(1f))
            if (permissionGranted) {
                IconButton(onClick = repository::refresh, enabled = !state.loading, modifier = Modifier.size(32.dp)) {
                    if (state.loading) CircularProgressIndicator(Modifier.size(16.dp), strokeWidth = 2.dp)
                    else Icon(Icons.Rounded.Refresh, "Odśwież pogodę", Modifier.size(18.dp))
                }
            }
        }

        if (!permissionGranted) {
            Spacer(Modifier.height(6.dp))
            OutlinedButton(
                onClick = { permissionLauncher.launch(Manifest.permission.ACCESS_COARSE_LOCATION) }
            ) {
                Icon(Icons.Rounded.LocationOn, null, Modifier.size(18.dp))
                Spacer(Modifier.width(6.dp))
                Text("Włącz lokalizację")
            }
            return@Column
        }

        state.data?.let { weather ->
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    if (weather.temperature.isNaN()) "—°" else "${String.format(Locale.US, "%.0f", weather.temperature)}°",
                    style = MaterialTheme.typography.headlineMedium,
                    fontWeight = FontWeight.Black
                )
                Spacer(Modifier.width(10.dp))
                Column(Modifier.weight(1f)) {
                    Text(
                        weather.place,
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = FontWeight.Bold,
                        maxLines = 1
                    )
                    Text(
                        buildString {
                            append(weather.description)
                            if (!weather.apparentTemperature.isNaN()) {
                                append(" • odczuwalna ")
                                append(String.format(Locale.US, "%.0f", weather.apparentTemperature))
                                append("°")
                            }
                        },
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 2
                    )
                }
                Column(horizontalAlignment = Alignment.End) {
                    if (!weather.windSpeed.isNaN()) {
                        Text(
                            "${String.format(Locale.US, "%.0f", weather.windSpeed)} km/h",
                            style = MaterialTheme.typography.labelMedium,
                            fontWeight = FontWeight.Bold
                        )
                        Text("wiatr", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }
        }

        state.error?.let {
            Spacer(Modifier.height(4.dp))
            Text(it, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.error)
        }
    }
}
