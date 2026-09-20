package pl.radiodrive.app.data

import android.content.Context
import pl.radiodrive.app.BuildConfig
import java.io.File

object AppMigration {
    private const val PREFS = "radiodrive_app_state"
    private const val CATALOG_SCHEMA = 4

    fun run(context: Context) {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        if (prefs.getInt("catalog_schema", 0) < CATALOG_SCHEMA) {
            runCatching { File(context.filesDir, "radiodrive_stations_pl.json").delete() }
        }
        prefs.edit()
            .putInt("catalog_schema", CATALOG_SCHEMA)
            .putInt("last_version_code", BuildConfig.VERSION_CODE)
            .putString("last_version_name", BuildConfig.VERSION_NAME)
            .apply()
    }
}
