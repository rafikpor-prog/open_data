package pl.radiodrive.app.sync

import android.accounts.Account
import android.app.Activity
import android.app.PendingIntent
import android.content.Context
import android.content.ContextWrapper
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.IntentSenderRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.CloudDone
import androidx.compose.material.icons.rounded.CloudOff
import androidx.compose.material.icons.rounded.CloudSync
import androidx.compose.material.icons.rounded.Logout
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.google.android.gms.auth.api.identity.AuthorizationRequest
import com.google.android.gms.auth.api.identity.AuthorizationResult
import com.google.android.gms.auth.api.identity.Identity
import com.google.android.gms.auth.api.identity.RevokeAccessRequest
import com.google.android.gms.common.api.Scope
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import java.util.Locale

enum class GoogleBackupAction { CONNECT, BACKUP, RESTORE }

data class GoogleSyncState(
    val accountEmail: String? = null,
    val syncing: Boolean = false,
    val lastBackupAt: Long = 0L,
    val lastRestoreAt: Long = 0L,
    val error: String? = null,
    val revision: Int = 0,
)

class GoogleDriveSyncManager private constructor(private val context: Context) {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
    private val _state = MutableStateFlow(
        GoogleSyncState(
            accountEmail = prefs.getString(KEY_EMAIL, null),
            lastBackupAt = prefs.getLong(KEY_LAST_BACKUP, 0L),
            lastRestoreAt = prefs.getLong(KEY_LAST_RESTORE, 0L),
        )
    )
    val state = _state.asStateFlow()

    init {
        scope.launch {
            delay(4_000L)
            while (isActive) {
                if (!prefs.getString(KEY_EMAIL, null).isNullOrBlank()) silentAuthorizeAndBackup()
                delay(30 * 60 * 1000L)
            }
        }
    }

    fun authorizationRequest(accountEmail: String? = null): AuthorizationRequest {
        val builder = AuthorizationRequest.builder()
            .setRequestedScopes(SCOPES)
        if (!accountEmail.isNullOrBlank()) {
            builder.setAccount(Account(accountEmail, "com.google"))
        }
        return builder.build()
    }

    fun silentAuthorizeAndSync() = silentAuthorizeAndBackup()

    fun silentAuthorizeAndBackup() {
        val email = prefs.getString(KEY_EMAIL, null) ?: return
        Identity.getAuthorizationClient(context)
            .authorize(authorizationRequest(email))
            .addOnSuccessListener { result ->
                if (!result.hasResolution()) handleAuthorizationResult(result, GoogleBackupAction.BACKUP)
            }
            .addOnFailureListener { error ->
                _state.value = _state.value.copy(error = friendlyAuthError(error))
            }
    }

    fun handleAuthorizationResult(
        result: AuthorizationResult,
        action: GoogleBackupAction = GoogleBackupAction.CONNECT,
    ) {
        val token = result.accessToken
        val email = runCatching { result.toGoogleSignInAccount()?.email }.getOrNull()
            ?: prefs.getString(KEY_EMAIL, null)

        if (token.isNullOrBlank()) {
            _state.value = _state.value.copy(error = "Google nie zwrócił tokenu dostępu do backupu.")
            return
        }

        if (!email.isNullOrBlank()) {
            prefs.edit().putString(KEY_EMAIL, email).apply()
        }
        _state.value = _state.value.copy(accountEmail = email, error = null)

        when (action) {
            GoogleBackupAction.CONNECT -> {
                _state.value = _state.value.copy(revision = _state.value.revision + 1)
            }
            GoogleBackupAction.BACKUP -> backupWithToken(token)
            GoogleBackupAction.RESTORE -> restoreWithToken(token)
        }
    }

    fun backupWithToken(token: String) {
        if (_state.value.syncing) return
        _state.value = _state.value.copy(syncing = true, error = null)
        scope.launch {
            runCatching { performBackup(token) }
                .onSuccess {
                    val now = System.currentTimeMillis()
                    prefs.edit().putLong(KEY_LAST_BACKUP, now).apply()
                    _state.value = _state.value.copy(
                        syncing = false,
                        lastBackupAt = now,
                        error = null,
                        revision = _state.value.revision + 1,
                    )
                }
                .onFailure { error ->
                    _state.value = _state.value.copy(
                        syncing = false,
                        error = error.message ?: "Nie udało się utworzyć backupu w Google Drive."
                    )
                }
        }
    }

    fun restoreWithToken(token: String) {
        if (_state.value.syncing) return
        _state.value = _state.value.copy(syncing = true, error = null)
        scope.launch {
            runCatching { performRestore(token) }
                .onSuccess {
                    val now = System.currentTimeMillis()
                    prefs.edit().putLong(KEY_LAST_RESTORE, now).apply()
                    _state.value = _state.value.copy(
                        syncing = false,
                        lastRestoreAt = now,
                        error = null,
                        revision = _state.value.revision + 1,
                    )
                }
                .onFailure { error ->
                    _state.value = _state.value.copy(
                        syncing = false,
                        error = error.message ?: "Nie udało się przywrócić backupu z Google Drive."
                    )
                }
        }
    }

    fun disconnect(accountEmail: String?, onDone: () -> Unit = {}) {
        val email = accountEmail ?: prefs.getString(KEY_EMAIL, null)
        if (email.isNullOrBlank()) {
            clearLocalAccount()
            onDone()
            return
        }
        val request = RevokeAccessRequest.builder()
            .setAccount(Account(email, "com.google"))
            .setScopes(SCOPES)
            .build()
        Identity.getAuthorizationClient(context)
            .revokeAccess(request)
            .addOnCompleteListener {
                clearLocalAccount()
                onDone()
            }
    }

    private fun clearLocalAccount() {
        prefs.edit().remove(KEY_EMAIL).remove(KEY_LAST_BACKUP).remove(KEY_LAST_RESTORE).apply()
        _state.value = GoogleSyncState(revision = _state.value.revision + 1)
    }

    private fun performBackup(token: String) {
        val local = SyncProfileStore.export(context)
        val fileId = findProfileFile(token)
        if (fileId == null) createProfileFile(token, local.toString())
        else updateProfileFile(token, fileId, local.toString())
    }

    private fun performRestore(token: String) {
        val fileId = findProfileFile(token)
            ?: error("Na tym koncie Google nie ma jeszcze backupu RadioDrive.")
        val cloud = JSONObject(downloadProfile(token, fileId))
        SyncProfileStore.import(context, cloud)
    }

    private fun findProfileFile(token: String): String? {
        val q = URLEncoder.encode("name='$PROFILE_FILE' and trashed=false", "UTF-8")
        val url = "https://www.googleapis.com/drive/v3/files?spaces=appDataFolder&q=$q&fields=files(id,name,modifiedTime)&pageSize=10"
        val json = JSONObject(request("GET", url, token))
        val files = json.optJSONArray("files") ?: return null
        return if (files.length() > 0) {
            files.optJSONObject(0)?.optString("id")?.takeIf { it.isNotBlank() }
        } else null
    }

    private fun downloadProfile(token: String, fileId: String): String =
        request("GET", "https://www.googleapis.com/drive/v3/files/$fileId?alt=media", token)

    private fun createProfileFile(token: String, content: String) {
        val boundary = "RadioDriveBoundary" + System.currentTimeMillis()
        val metadata = JSONObject()
            .put("name", PROFILE_FILE)
            .put("parents", JSONArray().put("appDataFolder"))
            .toString()

        val body = buildString {
            append("--$boundary\r\n")
            append("Content-Type: application/json; charset=UTF-8\r\n\r\n")
            append(metadata)
            append("\r\n--$boundary\r\n")
            append("Content-Type: application/json\r\n\r\n")
            append(content)
            append("\r\n--$boundary--\r\n")
        }

        request(
            "POST",
            "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id",
            token,
            body,
            "multipart/related; boundary=$boundary"
        )
    }

    private fun updateProfileFile(token: String, fileId: String, content: String) {
        request(
            "PATCH",
            "https://www.googleapis.com/upload/drive/v3/files/$fileId?uploadType=media",
            token,
            content,
            "application/json; charset=UTF-8"
        )
    }

    private fun request(
        method: String,
        url: String,
        token: String,
        body: String? = null,
        contentType: String? = null,
    ): String {
        val connection = (URL(url).openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = 12_000
            readTimeout = 20_000
            setRequestProperty("Authorization", "Bearer $token")
            setRequestProperty("Accept", "application/json")
            if (contentType != null) setRequestProperty("Content-Type", contentType)
            if (body != null) doOutput = true
        }

        try {
            if (body != null) {
                connection.outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) }
            }
            val code = connection.responseCode
            val stream = if (code in 200..299) connection.inputStream else connection.errorStream
            val responseText = stream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
            if (code !in 200..299) {
                error("Google Drive HTTP $code: " + responseText.take(180))
            }
            return responseText
        } finally {
            connection.disconnect()
        }
    }

    private fun friendlyAuthError(error: Throwable): String {
        val msg = error.message.orEmpty()
        return if ("10" in msg || "DEVELOPER_ERROR" in msg.uppercase(Locale.ROOT)) {
            "Logowanie Google wymaga zarejestrowania klienta OAuth dla pakietu RadioDrive i jego certyfikatu podpisu."
        } else {
            msg.ifBlank { "Nie udało się połączyć z kontem Google." }
        }
    }

    companion object {
        const val DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.appdata"
        private val SCOPES = listOf(Scope(DRIVE_SCOPE), Scope("email"))
        private const val PROFILE_FILE = "radiodrive-sync.json"
        private const val PREFS = "radiodrive_google_sync"
        private const val KEY_EMAIL = "account_email"
        private const val KEY_LAST_BACKUP = "last_backup"
        private const val KEY_LAST_RESTORE = "last_restore"

        @Volatile private var INSTANCE: GoogleDriveSyncManager? = null

        fun get(context: Context): GoogleDriveSyncManager =
            INSTANCE ?: synchronized(this) {
                INSTANCE ?: GoogleDriveSyncManager(context.applicationContext).also { INSTANCE = it }
            }
    }
}

@Composable
fun GoogleSyncDialog(
    onDismiss: () -> Unit,
    onSynced: () -> Unit,
) {
    val context = LocalContext.current
    val activity = context.findActivity()
    val manager = remember { GoogleDriveSyncManager.get(context.applicationContext) }
    val state by manager.state.collectAsState()
    var pendingAction by remember { mutableStateOf(GoogleBackupAction.CONNECT) }
    var confirmRestore by remember { mutableStateOf(false) }

    LaunchedEffect(state.revision) {
        if (state.revision > 0) onSynced()
    }

    val launcher = rememberLauncherForActivityResult(
        ActivityResultContracts.StartIntentSenderForResult()
    ) { result ->
        if (result.resultCode == Activity.RESULT_OK && result.data != null && activity != null) {
            runCatching {
                Identity.getAuthorizationClient(activity)
                    .getAuthorizationResultFromIntent(result.data!!)
            }.onSuccess { auth ->
                manager.handleAuthorizationResult(auth, pendingAction)
            }
        }
    }

    fun beginAuthorization(action: GoogleBackupAction, forceAccountSelection: Boolean = false) {
        val act = activity ?: return
        pendingAction = action
        val request = manager.authorizationRequest(
            if (forceAccountSelection) null else state.accountEmail
        )
        Identity.getAuthorizationClient(act)
            .authorize(request)
            .addOnSuccessListener { authResult ->
                if (authResult.hasResolution()) {
                    val pending: PendingIntent = authResult.pendingIntent ?: return@addOnSuccessListener
                    launcher.launch(IntentSenderRequest.Builder(pending.intentSender).build())
                } else {
                    manager.handleAuthorizationResult(authResult, action)
                }
            }
            .addOnFailureListener { }
    }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Rounded.CloudSync, null)
                Spacer(Modifier.width(10.dp))
                Text("Konto Google i backup", fontWeight = FontWeight.Black)
            }
        },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Surface(shape = RoundedCornerShape(18.dp), color = MaterialTheme.colorScheme.surfaceVariant) {
                    Column(Modifier.fillMaxWidth().padding(14.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                if (state.accountEmail != null) Icons.Rounded.CloudDone else Icons.Rounded.CloudOff,
                                null
                            )
                            Spacer(Modifier.width(8.dp))
                            Column {
                                Text(state.accountEmail ?: "Nie jesteś zalogowany", fontWeight = FontWeight.Bold)
                                Text(
                                    if (state.accountEmail != null) {
                                        "Backup RadioDrive jest zapisywany w prywatnym folderze aplikacji na Google Drive."
                                    } else {
                                        "Zaloguj konto Google, aby przenosić ustawienia między telefonem i tabletem."
                                    },
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        }
                    }
                }

                Text(
                    "Backup obejmuje własne stacje i streamy, zmienione logotypy i adresy, ulubione, historię oraz ustawienia katalogu.",
                    style = MaterialTheme.typography.bodyMedium
                )

                state.error?.let {
                    Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
                }

                if (state.syncing) LinearProgressIndicator(Modifier.fillMaxWidth())

                if (state.accountEmail == null) {
                    Button(
                        onClick = { beginAuthorization(GoogleBackupAction.CONNECT, true) },
                        enabled = !state.syncing,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Icon(Icons.Rounded.CloudSync, null)
                        Spacer(Modifier.width(8.dp))
                        Text("Zaloguj kontem Google")
                    }
                } else {
                    Button(
                        onClick = { beginAuthorization(GoogleBackupAction.BACKUP) },
                        enabled = !state.syncing,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Icon(Icons.Rounded.CloudDone, null)
                        Spacer(Modifier.width(8.dp))
                        Text("Utwórz backup teraz")
                    }
                    OutlinedButton(
                        onClick = { confirmRestore = true },
                        enabled = !state.syncing,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Icon(Icons.Rounded.CloudSync, null)
                        Spacer(Modifier.width(8.dp))
                        Text("Przywróć backup z Google Drive")
                    }
                    Text(
                        buildString {
                            if (state.lastBackupAt > 0L) append("Backup jest dostępny na koncie Google. ")
                            if (state.lastRestoreAt > 0L) append("Ostatnie przywrócenie zakończone.")
                        }.ifBlank { "Nie wykonano jeszcze backupu w tej instalacji." },
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    OutlinedButton(
                        onClick = { manager.disconnect(state.accountEmail) },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Icon(Icons.Rounded.Logout, null)
                        Spacer(Modifier.width(8.dp))
                        Text("Wyloguj / odłącz konto")
                    }
                }
            }
        },
        confirmButton = {
            TextButton(onClick = onDismiss) { Text("Zamknij") }
        }
    )

    if (confirmRestore) {
        AlertDialog(
            onDismissRequest = { confirmRestore = false },
            title = { Text("Przywrócić backup?") },
            text = {
                Text("Dane zapisane obecnie na tym urządzeniu zostaną zastąpione ustawieniami z backupu RadioDrive na Google Drive.")
            },
            confirmButton = {
                Button(onClick = {
                    confirmRestore = false
                    beginAuthorization(GoogleBackupAction.RESTORE)
                }) { Text("Przywróć") }
            },
            dismissButton = {
                TextButton(onClick = { confirmRestore = false }) { Text("Anuluj") }
            }
        )
    }
}
private tailrec fun Context.findActivity(): Activity? = when (this) {
    is Activity -> this
    is ContextWrapper -> baseContext.findActivity()
    else -> null
}
