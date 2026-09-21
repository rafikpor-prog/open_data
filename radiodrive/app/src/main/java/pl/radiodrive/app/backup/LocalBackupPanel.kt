package pl.radiodrive.app.backup

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.CheckCircle
import androidx.compose.material.icons.rounded.Download
import androidx.compose.material.icons.rounded.FolderOpen
import androidx.compose.material.icons.rounded.Save
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import pl.radiodrive.app.sync.SyncProfileStore
import pl.radiodrive.app.ui.theme.RadioCyan
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun LocalBackupPanel(
    onRestored: () -> Unit,
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var message by remember { mutableStateOf<String?>(null) }
    var error by remember { mutableStateOf<String?>(null) }
    var pendingRestore by remember { mutableStateOf<Uri?>(null) }
    var busy by remember { mutableStateOf(false) }

    val exportLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.CreateDocument("application/json")
    ) { uri ->
        if (uri != null) {
            busy = true
            scope.launch {
                val result = runCatching {
                    withContext(Dispatchers.IO) {
                        val root = SyncProfileStore.export(context.applicationContext)
                            .put("exportedBy", "RadioDrive")
                            .put("exportedAt", System.currentTimeMillis())
                        context.contentResolver.openOutputStream(uri, "w")?.use { stream ->
                            stream.write(root.toString(2).toByteArray(Charsets.UTF_8))
                        } ?: error("Nie udało się otworzyć pliku do zapisu.")
                    }
                }
                busy = false
                result.onSuccess {
                    error = null
                    message = "Kopia ustawień została zapisana w wybranym pliku."
                }.onFailure {
                    message = null
                    error = it.message ?: "Nie udało się zapisać kopii ustawień."
                }
            }
        }
    }

    val importLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.OpenDocument()
    ) { uri ->
        if (uri != null) pendingRestore = uri
    }

    Surface(
        shape = RoundedCornerShape(28.dp),
        color = MaterialTheme.colorScheme.surfaceVariant,
        border = androidx.compose.foundation.BorderStroke(1.dp, RadioCyan.copy(alpha = .28f))
    ) {
        Column(Modifier.fillMaxWidth().padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Surface(shape = CircleShape, color = RadioCyan.copy(alpha = .12f)) {
                    Icon(Icons.Rounded.Save, null, Modifier.padding(10.dp), tint = RadioCyan)
                }
                Spacer(Modifier.width(12.dp))
                Column(Modifier.weight(1f)) {
                    Text("Kopia ustawień RadioDrive", fontWeight = FontWeight.Black, style = MaterialTheme.typography.titleMedium)
                    Text(
                        "Bez konta. Zapisujesz plik lokalnie i możesz przenieść go na inne urządzenie.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            if (busy) LinearProgressIndicator(Modifier.fillMaxWidth())

            Button(
                onClick = {
                    val stamp = SimpleDateFormat("yyyy-MM-dd_HH-mm", Locale.US).format(Date())
                    exportLauncher.launch("RadioDrive-backup-$stamp.json")
                },
                enabled = !busy,
                modifier = Modifier.fillMaxWidth()
            ) {
                Icon(Icons.Rounded.Download, null)
                Spacer(Modifier.width(8.dp))
                Text("Eksportuj ustawienia do pliku")
            }

            OutlinedButton(
                onClick = { importLauncher.launch(arrayOf("application/json", "text/plain", "*/*")) },
                enabled = !busy,
                modifier = Modifier.fillMaxWidth()
            ) {
                Icon(Icons.Rounded.FolderOpen, null)
                Spacer(Modifier.width(8.dp))
                Text("Przywróć ustawienia z pliku")
            }

            Text(
                "Plik zawiera: ulubione, własne stacje, adresy streamów, logotypy, historię oraz listę ukrytych stacji.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            message?.let {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Rounded.CheckCircle, null, tint = RadioCyan, modifier = Modifier.size(18.dp))
                    Spacer(Modifier.width(7.dp))
                    Text(it, style = MaterialTheme.typography.bodySmall)
                }
            }
            error?.let {
                Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
            }
        }
    }

    pendingRestore?.let { uri ->
        AlertDialog(
            onDismissRequest = { pendingRestore = null },
            title = { Text("Przywrócić ustawienia?") },
            text = {
                Text("Obecne ustawienia RadioDrive na tym urządzeniu zostaną zastąpione danymi z wybranego pliku.")
            },
            confirmButton = {
                Button(onClick = {
                    pendingRestore = null
                    busy = true
                    scope.launch {
                        val result = runCatching {
                            withContext(Dispatchers.IO) {
                                val raw = context.contentResolver.openInputStream(uri)
                                    ?.bufferedReader(Charsets.UTF_8)
                                    ?.use { it.readText() }
                                    ?: error("Nie udało się odczytać pliku.")
                                val root = JSONObject(raw)
                                require(root.optInt("schema", 0) in 1..10) {
                                    "To nie jest prawidłowy plik kopii RadioDrive."
                                }
                                SyncProfileStore.import(context.applicationContext, root)
                            }
                        }
                        busy = false
                        result.onSuccess {
                            error = null
                            message = "Ustawienia zostały przywrócone."
                            onRestored()
                        }.onFailure {
                            message = null
                            error = it.message ?: "Nie udało się przywrócić ustawień."
                        }
                    }
                }) { Text("Przywróć") }
            },
            dismissButton = {
                TextButton(onClick = { pendingRestore = null }) { Text("Anuluj") }
            }
        )
    }
}
