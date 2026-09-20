package pl.radiodrive.app.road

import android.app.Notification
import android.app.NotificationManager
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.provider.Settings
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.DirectionsCar
import androidx.compose.material.icons.rounded.Map
import androidx.compose.material.icons.rounded.NotificationsActive
import androidx.compose.material.icons.rounded.OpenInNew
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import pl.radiodrive.app.ui.theme.RadioAmber
import pl.radiodrive.app.ui.theme.RadioCyan

data class RoadAssistState(
    val googleMapsInstruction: String? = null,
    val yanosikAlert: String? = null,
    val updatedAt: Long = 0L,
)

object RoadAssistStore {
    private val _state = MutableStateFlow(RoadAssistState())
    val state = _state.asStateFlow()

    fun updateGoogleMaps(text: String) {
        if (text.isNotBlank()) _state.value = _state.value.copy(googleMapsInstruction = text, updatedAt = System.currentTimeMillis())
    }

    fun updateYanosik(text: String) {
        if (text.isNotBlank()) _state.value = _state.value.copy(yanosikAlert = text, updatedAt = System.currentTimeMillis())
    }
}

class RoadNotificationListenerService : NotificationListenerService() {

    override fun onListenerConnected() {
        super.onListenerConnected()
        activeNotifications?.forEach(::capture)
    }

    override fun onNotificationPosted(sbn: StatusBarNotification?) {
        sbn?.let(::capture)
    }

    private fun capture(sbn: StatusBarNotification) {
        val text = notificationText(sbn.notification)
        if (text.isBlank()) return
        when (sbn.packageName) {
            GOOGLE_MAPS -> RoadAssistStore.updateGoogleMaps(text)
            YANOSIK -> RoadAssistStore.updateYanosik(text)
        }
    }

    private fun notificationText(notification: Notification): String {
        val extras = notification.extras
        val values = listOf(
            extras.getCharSequence(Notification.EXTRA_TITLE),
            extras.getCharSequence(Notification.EXTRA_TEXT),
            extras.getCharSequence(Notification.EXTRA_BIG_TEXT),
            extras.getCharSequence(Notification.EXTRA_SUB_TEXT),
        )
            .mapNotNull { it?.toString()?.trim() }
            .filter { it.isNotBlank() }
            .distinct()

        return values
            .filterNot { it.equals("Google Maps", true) || it.equals("Yanosik", true) }
            .joinToString(" • ")
            .take(360)
    }

    companion object {
        const val GOOGLE_MAPS = "com.google.android.apps.maps"
        const val YANOSIK = "pl.neptis.yanosik.mobi.android"
    }
}

@Composable
fun RoadAssistPanel() {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val state by RoadAssistStore.state.collectAsState()
    var accessGranted by remember { mutableStateOf(hasNotificationAccess(context)) }

    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) accessGranted = hasNotificationAccess(context)
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    Surface(shape = RoundedCornerShape(26.dp), color = MaterialTheme.colorScheme.surfaceVariant) {
        Column(Modifier.fillMaxWidth().padding(18.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Rounded.DirectionsCar, null, tint = RadioCyan)
                Spacer(Modifier.width(10.dp))
                Column(Modifier.weight(1f)) {
                    Text("Tryb jazdy", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Black)
                    Text("Radio + wskazówki z aktywnej nawigacji", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }

            Spacer(Modifier.height(12.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                AssistChip(
                    onClick = { launchPackage(context, RoadNotificationListenerService.GOOGLE_MAPS, "https://play.google.com/store/apps/details?id=com.google.android.apps.maps") },
                    label = { Text("Google Maps") },
                    leadingIcon = { Icon(Icons.Rounded.Map, null, Modifier.size(18.dp)) }
                )
                AssistChip(
                    onClick = { launchPackage(context, RoadNotificationListenerService.YANOSIK, "https://play.google.com/store/apps/details?id=pl.neptis.yanosik.mobi.android") },
                    label = { Text("Yanosik") },
                    leadingIcon = { Icon(Icons.Rounded.OpenInNew, null, Modifier.size(18.dp)) }
                )
            }

            Spacer(Modifier.height(10.dp))
            if (!accessGranted) {
                Text(
                    "Aby pokazać w RadioDrive tekst następnego manewru z Google Maps i ostrzeżenia wysłane przez Yanosik, włącz opcjonalny dostęp do powiadomień. RadioDrive filtruje tylko te dwie aplikacje.",
                    style = MaterialTheme.typography.bodySmall
                )
                Spacer(Modifier.height(8.dp))
                Button(onClick = { openNotificationAccess(context) }) {
                    Icon(Icons.Rounded.NotificationsActive, null)
                    Spacer(Modifier.width(8.dp))
                    Text("Włącz informacje z nawigacji")
                }
            } else {
                DriveMessage("Google Maps", state.googleMapsInstruction ?: "Uruchom nawigację, aby tutaj pojawił się bieżący manewr.", RadioCyan)
                Spacer(Modifier.height(8.dp))
                DriveMessage("Yanosik", state.yanosikAlert ?: "Gdy Yanosik wyśle ostrzeżenie drogowe, RadioDrive pokaże jego treść tutaj.", RadioAmber)
            }

            Spacer(Modifier.height(8.dp))
            Text(
                "Na Android Auto mapa i prowadzenie są renderowane przez Google Maps lub Yanosik. RadioDrive pozostaje odtwarzaczem multimediów obok nawigacji.",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
private fun DriveMessage(label: String, text: String, accent: androidx.compose.ui.graphics.Color) {
    Surface(shape = RoundedCornerShape(18.dp), color = MaterialTheme.colorScheme.surface) {
        Column(Modifier.fillMaxWidth().padding(12.dp)) {
            Text(label.uppercase(), style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Black, color = accent)
            Text(text, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold)
        }
    }
}

private fun hasNotificationAccess(context: Context): Boolean {
    val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
    return manager.isNotificationListenerAccessGranted(ComponentName(context, RoadNotificationListenerService::class.java))
}

private fun openNotificationAccess(context: Context) {
    val component = ComponentName(context, RoadNotificationListenerService::class.java)
    val detail = Intent(Settings.ACTION_NOTIFICATION_LISTENER_DETAIL_SETTINGS)
        .putExtra(Settings.EXTRA_NOTIFICATION_LISTENER_COMPONENT_NAME, component)
        .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    val generic = Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    runCatching { context.startActivity(detail) }.recoverCatching { context.startActivity(generic) }
}

private fun launchPackage(context: Context, packageName: String, fallbackUrl: String) {
    val launch = context.packageManager.getLaunchIntentForPackage(packageName)
    if (launch != null) {
        launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        context.startActivity(launch)
    } else {
        runCatching {
            context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(fallbackUrl)).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        }
    }
}
