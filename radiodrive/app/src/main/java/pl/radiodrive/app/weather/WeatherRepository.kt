package pl.radiodrive.app.weather

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.Geocoder
import android.location.Location
import android.location.LocationManager
import android.os.Build
import android.os.CancellationSignal
import androidx.core.content.ContextCompat
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.Locale
import kotlin.coroutines.resume

data class WeatherData(
    val place: String,
    val temperature: Double,
    val apparentTemperature: Double,
    val humidity: Int,
    val weatherCode: Int,
    val windSpeed: Double,
    val windGusts: Double,
    val precipitation: Double,
    val minTemperature: Double?,
    val maxTemperature: Double?,
    val precipitationProbability: Int?,
) {
    val description: String get() = weatherDescription(weatherCode)
}

data class WeatherState(
    val loading: Boolean = false,
    val data: WeatherData? = null,
    val error: String? = null,
)

class WeatherRepository private constructor(private val context: Context) {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val _state = MutableStateFlow(WeatherState())
    val state: StateFlow<WeatherState> = _state.asStateFlow()

    fun refresh() {
        if (_state.value.loading) return
        if (!hasLocationPermission()) {
            _state.value = WeatherState(error = "Włącz przybliżoną lokalizację, aby pobrać pogodę.")
            return
        }

        _state.value = _state.value.copy(loading = true, error = null)
        scope.launch {
            runCatching {
                val location = currentLocation()
                    ?: error("Nie udało się ustalić lokalizacji telefonu. Sprawdź, czy lokalizacja systemowa jest włączona.")
                fetchWeather(location)
            }.onSuccess {
                _state.value = WeatherState(data = it)
            }.onFailure {
                _state.value = WeatherState(
                    data = _state.value.data,
                    error = it.message ?: "Nie udało się pobrać pogody."
                )
            }
        }
    }

    private fun hasLocationPermission(): Boolean =
        ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION) ==
            PackageManager.PERMISSION_GRANTED

    private suspend fun currentLocation(): Location? {
        val manager = context.getSystemService(Context.LOCATION_SERVICE) as LocationManager
        val providers = listOf(
            LocationManager.NETWORK_PROVIDER,
            LocationManager.GPS_PROVIDER,
            LocationManager.PASSIVE_PROVIDER
        ).filter { provider ->
            runCatching { manager.isProviderEnabled(provider) }.getOrDefault(false)
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            for (provider in providers) {
                val result = suspendCancellableCoroutine<Location?> { continuation ->
                    val signal = CancellationSignal()
                    continuation.invokeOnCancellation { signal.cancel() }
                    runCatching {
                        manager.getCurrentLocation(
                            provider,
                            signal,
                            ContextCompat.getMainExecutor(context)
                        ) { location ->
                            if (continuation.isActive) continuation.resume(location)
                        }
                    }.onFailure {
                        if (continuation.isActive) continuation.resume(null)
                    }
                }
                if (result != null) return result
            }
        }

        return bestLastKnown(manager)
    }

    private fun bestLastKnown(manager: LocationManager): Location? {
        if (!hasLocationPermission()) return null
        return manager.getProviders(true)
            .mapNotNull { provider ->
                runCatching { manager.getLastKnownLocation(provider) }.getOrNull()
            }
            .maxByOrNull { it.time }
    }

    private suspend fun fetchWeather(location: Location): WeatherData = withContext(Dispatchers.IO) {
        val lat = String.format(Locale.US, "%.4f", location.latitude)
        val lon = String.format(Locale.US, "%.4f", location.longitude)
        val endpoint =
            "https://api.open-meteo.com/v1/forecast" +
                "?latitude=$lat&longitude=$lon" +
                "&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m,wind_gusts_10m,precipitation" +
                "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max" +
                "&forecast_days=1&timezone=auto"

        val connection = (URL(endpoint).openConnection() as HttpURLConnection).apply {
            requestMethod = "GET"
            connectTimeout = 10_000
            readTimeout = 15_000
            setRequestProperty("User-Agent", "RadioDrive/2.1 Android")
            setRequestProperty("Accept", "application/json")
        }

        val raw = try {
            if (connection.responseCode !in 200..299) {
                error("Serwis pogodowy zwrócił HTTP ${connection.responseCode}.")
            }
            connection.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() }
        } finally {
            connection.disconnect()
        }

        val root = JSONObject(raw)
        val current = root.getJSONObject("current")
        val daily = root.optJSONObject("daily")
        WeatherData(
            place = resolvePlace(location),
            temperature = current.optDouble("temperature_2m", Double.NaN),
            apparentTemperature = current.optDouble("apparent_temperature", Double.NaN),
            humidity = current.optInt("relative_humidity_2m", -1),
            weatherCode = current.optInt("weather_code", -1),
            windSpeed = current.optDouble("wind_speed_10m", Double.NaN),
            windGusts = current.optDouble("wind_gusts_10m", Double.NaN),
            precipitation = current.optDouble("precipitation", 0.0),
            maxTemperature = daily?.optJSONArray("temperature_2m_max")?.optDouble(0)?.takeUnless { it.isNaN() },
            minTemperature = daily?.optJSONArray("temperature_2m_min")?.optDouble(0)?.takeUnless { it.isNaN() },
            precipitationProbability = daily?.optJSONArray("precipitation_probability_max")?.optInt(0)?.takeIf { it >= 0 },
        )
    }

    @Suppress("DEPRECATION")
    private fun resolvePlace(location: Location): String = runCatching {
        if (!Geocoder.isPresent()) return@runCatching "Twoja lokalizacja"
        val address = Geocoder(context, Locale("pl", "PL"))
            .getFromLocation(location.latitude, location.longitude, 1)
            ?.firstOrNull()
        address?.locality
            ?: address?.subAdminArea
            ?: address?.adminArea
            ?: "Twoja lokalizacja"
    }.getOrDefault("Twoja lokalizacja")

    companion object {
        @Volatile private var INSTANCE: WeatherRepository? = null

        fun get(context: Context): WeatherRepository =
            INSTANCE ?: synchronized(this) {
                INSTANCE ?: WeatherRepository(context.applicationContext).also { INSTANCE = it }
            }
    }
}

fun weatherDescription(code: Int): String = when (code) {
    0 -> "Bezchmurnie"
    1 -> "Przeważnie pogodnie"
    2 -> "Częściowe zachmurzenie"
    3 -> "Pochmurno"
    45, 48 -> "Mgła"
    51, 53, 55 -> "Mżawka"
    56, 57 -> "Marznąca mżawka"
    61 -> "Lekki deszcz"
    63 -> "Deszcz"
    65 -> "Intensywny deszcz"
    66, 67 -> "Marznący deszcz"
    71, 73, 75, 77 -> "Śnieg"
    80, 81, 82 -> "Przelotny deszcz"
    85, 86 -> "Przelotny śnieg"
    95 -> "Burza"
    96, 99 -> "Burza z gradem"
    else -> "Warunki pogodowe"
}
