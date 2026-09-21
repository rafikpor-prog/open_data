package pl.przemysl.cloud.mobile;

import android.app.Activity;
import android.app.AlertDialog;
import android.app.DownloadManager;
import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.net.http.SslError;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.ViewParent;
import android.view.WindowManager;
import android.webkit.CookieManager;
import android.webkit.SslErrorHandler;
import android.webkit.URLUtil;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageButton;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

public class MainActivity extends Activity {
    private static final int FILE_CHOOSER = 7001;
    private static final String PREFS = "cloud_um_mobile";
    private static final String PREF_URL = "server_url";
    private WebView web;
    private LinearLayout bottom;
    private TextView title;
    private ValueCallback<Uri[]> fileCallback;
    private String baseUrl;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setFlags(WindowManager.LayoutParams.FLAG_SECURE, WindowManager.LayoutParams.FLAG_SECURE);
        CookieManager.getInstance().setAcceptCookie(true);
        baseUrl = getSharedPreferences(PREFS, MODE_PRIVATE).getString(PREF_URL, "");
        if (baseUrl.isEmpty()) showSetup(); else buildBrowser(true);
    }

    private int dp(int v) { return Math.round(v * getResources().getDisplayMetrics().density); }

    private TextView text(String value, int sp, int color) {
        TextView v = new TextView(this);
        v.setText(value);
        v.setTextSize(sp);
        v.setTextColor(color);
        return v;
    }

    private void showSetup() {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(dp(28), dp(36), dp(28), dp(28));
        box.setBackgroundColor(Color.rgb(244, 247, 251));

        TextView h = text("Cloud UM Przemyśl", 26, Color.rgb(15, 23, 42));
        h.setTypeface(null, 1);
        box.addView(h, new LinearLayout.LayoutParams(-1, -2));

        TextView p = text(
            "Podaj pełny adres HTTPS systemu. Aplikacja nie przechowuje hasła; logowanie, MFA i uprawnienia pozostają po stronie systemu.",
            15, Color.rgb(71, 85, 105)
        );
        LinearLayout.LayoutParams pp = new LinearLayout.LayoutParams(-1, -2);
        pp.setMargins(0, dp(10), 0, dp(22));
        box.addView(p, pp);

        EditText input = new EditText(this);
        input.setSingleLine(true);
        input.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        input.setHint("https://cloud.twoja-domena.pl");
        box.addView(input, new LinearLayout.LayoutParams(-1, dp(56)));

        Button save = new Button(this);
        save.setText("Połącz z systemem");
        LinearLayout.LayoutParams bp = new LinearLayout.LayoutParams(-1, dp(56));
        bp.setMargins(0, dp(18), 0, 0);
        box.addView(save, bp);

        TextView foot = text("Dozwolone jest wyłącznie HTTPS. Ruch nieszyfrowany HTTP jest blokowany.", 13, Color.rgb(100, 116, 139));
        LinearLayout.LayoutParams fp = new LinearLayout.LayoutParams(-1, -2);
        fp.setMargins(0, dp(18), 0, 0);
        box.addView(foot, fp);

        setContentView(box);
        save.setOnClickListener(v -> {
            String u = normalizeUrl(input.getText().toString());
            if (u == null) {
                input.setError("Wpisz poprawny adres zaczynający się od https://");
                return;
            }
            baseUrl = u;
            getSharedPreferences(PREFS, MODE_PRIVATE).edit().putString(PREF_URL, u).apply();
            buildBrowser(true);
        });
    }

    private String normalizeUrl(String raw) {
        try {
            raw = raw.trim();
            while (raw.endsWith("/")) raw = raw.substring(0, raw.length() - 1);
            Uri u = Uri.parse(raw);
            if (!"https".equalsIgnoreCase(u.getScheme()) || u.getHost() == null || u.getHost().isEmpty()) return null;
            return raw;
        } catch (Exception e) {
            return null;
        }
    }

    private void buildBrowser(boolean loadHome) {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.WHITE);
        root.addView(buildTopBar(), new LinearLayout.LayoutParams(-1, dp(52)));

        web = new WebView(this);
        configureWebView();
        root.addView(web, new LinearLayout.LayoutParams(-1, 0, 1f));

        bottom = buildBottomBar();
        root.addView(bottom, new LinearLayout.LayoutParams(-1, dp(62)));

        setContentView(root);
        if (loadHome) openRoute("/");
    }

    private View buildTopBar() {
        LinearLayout bar = new LinearLayout(this);
        bar.setGravity(Gravity.CENTER_VERTICAL);
        bar.setPadding(dp(4), 0, dp(4), 0);
        bar.setBackgroundColor(Color.rgb(15, 23, 42));

        ImageButton back = new ImageButton(this);
        back.setImageResource(android.R.drawable.ic_media_previous);
        back.setContentDescription("Wstecz");
        back.setBackgroundColor(Color.TRANSPARENT);
        back.setColorFilter(Color.WHITE);
        back.setOnClickListener(v -> onBackPressed());
        bar.addView(back, new LinearLayout.LayoutParams(dp(48), dp(48)));

        title = text("Cloud UM", 18, Color.WHITE);
        title.setTypeface(null, 1);
        title.setSingleLine(true);
        title.setEllipsize(android.text.TextUtils.TruncateAt.END);
        LinearLayout.LayoutParams tp = new LinearLayout.LayoutParams(0, -2, 1f);
        tp.setMargins(dp(6), 0, dp(6), 0);
        bar.addView(title, tp);

        ImageButton reload = new ImageButton(this);
        reload.setImageResource(android.R.drawable.ic_popup_sync);
        reload.setContentDescription("Odśwież");
        reload.setBackgroundColor(Color.TRANSPARENT);
        reload.setColorFilter(Color.WHITE);
        reload.setOnClickListener(v -> web.reload());
        bar.addView(reload, new LinearLayout.LayoutParams(dp(48), dp(48)));

        ImageButton settings = new ImageButton(this);
        settings.setImageResource(android.R.drawable.ic_menu_manage);
        settings.setContentDescription("Ustawienia");
        settings.setBackgroundColor(Color.TRANSPARENT);
        settings.setColorFilter(Color.WHITE);
        settings.setOnClickListener(v -> showSettings());
        bar.addView(settings, new LinearLayout.LayoutParams(dp(48), dp(48)));

        return bar;
    }

    private LinearLayout buildBottomBar() {
        LinearLayout bar = new LinearLayout(this);
        bar.setOrientation(LinearLayout.HORIZONTAL);
        bar.setGravity(Gravity.CENTER);
        bar.setBackgroundColor(Color.WHITE);
        bar.setElevation(dp(8));
        addNav(bar, "Dashboard", "/");
        addNav(bar, "Systemy", "/it-systems");
        addNav(bar, "Incydenty", "/incidents");
        addNav(bar, "Dostępy", "/system-access");
        Button more = navButton("Więcej");
        more.setOnClickListener(v -> showMore());
        bar.addView(more, new LinearLayout.LayoutParams(0, -1, 1f));
        return bar;
    }

    private Button navButton(String label) {
        Button b = new Button(this);
        b.setText(label);
        b.setTextSize(11);
        b.setTextColor(Color.rgb(15, 23, 42));
        b.setBackgroundColor(Color.TRANSPARENT);
        b.setAllCaps(false);
        b.setPadding(dp(2), 0, dp(2), 0);
        return b;
    }

    private void addNav(LinearLayout parent, String label, String route) {
        Button b = navButton(label);
        b.setOnClickListener(v -> openRoute(route));
        parent.addView(b, new LinearLayout.LayoutParams(0, -1, 1f));
    }

    private void configureWebView() {
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(false);
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(false);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        s.setSupportMultipleWindows(false);
        s.setJavaScriptCanOpenWindowsAutomatically(false);
        s.setSaveFormData(false);
        s.setBuiltInZoomControls(false);
        s.setDisplayZoomControls(false);
        s.setUserAgentString(s.getUserAgentString() + " CloudUMAndroid/1.0.0");

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            WebView.startSafeBrowsing(this, ok -> {});
        }

        CookieManager.getInstance().setAcceptThirdPartyCookies(web, false);

        web.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri u = request.getUrl();
                if (isInternal(u)) return false;
                openExternal(u);
                return true;
            }

            @Override public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                updateChrome(url);
                injectMobileCss();
            }

            @Override public void onReceivedSslError(WebView view, SslErrorHandler handler, SslError error) {
                handler.cancel();
                Toast.makeText(MainActivity.this, "Błąd certyfikatu TLS. Połączenie zostało zablokowane.", Toast.LENGTH_LONG).show();
            }

            @Override public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) {
                    Toast.makeText(MainActivity.this, "Nie udało się połączyć z systemem.", Toast.LENGTH_LONG).show();
                }
            }
        });

        web.setWebChromeClient(new WebChromeClient() {
            @Override public void onReceivedTitle(WebView view, String value) {
                if (value != null && !value.trim().isEmpty()) {
                    String t = value.trim();
                    title.setText(t.length() > 36 ? t.substring(0, 36) + "…" : t);
                }
            }

            @Override public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback, FileChooserParams params) {
                if (fileCallback != null) fileCallback.onReceiveValue(null);
                fileCallback = callback;
                Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
                intent.addCategory(Intent.CATEGORY_OPENABLE);
                intent.setType("*/*");
                intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, params != null && params.getMode() == FileChooserParams.MODE_OPEN_MULTIPLE);
                try {
                    startActivityForResult(Intent.createChooser(intent, "Wybierz plik"), FILE_CHOOSER);
                    return true;
                } catch (Exception e) {
                    fileCallback = null;
                    return false;
                }
            }
        });

        web.setDownloadListener((url, userAgent, contentDisposition, mimetype, contentLength) ->
            download(url, userAgent, contentDisposition, mimetype)
        );
    }

    private void injectMobileCss() {
        String js = "(function(){var id='cloud-android-shell';if(!document.getElementById(id)){var s=document.createElement('style');s.id=id;s.textContent='.sidebar,.mobile-topbar,.sidebar-overlay{display:none!important}.layout{display:block!important;min-height:0!important}.main{padding:12px!important;margin:0!important;max-width:100vw!important}.userbar{display:none!important}.page-head{margin-top:0!important}.card{border-radius:14px!important}body{padding-bottom:2px!important}';document.head.appendChild(s);}})();";
        web.evaluateJavascript(js, null);
    }

    private boolean isInternal(Uri uri) {
        try {
            Uri base = Uri.parse(baseUrl);
            return "https".equalsIgnoreCase(uri.getScheme())
                && base.getHost() != null
                && base.getHost().equalsIgnoreCase(uri.getHost())
                && normalizedPort(base) == normalizedPort(uri);
        } catch (Exception e) {
            return false;
        }
    }

    private int normalizedPort(Uri u) {
        return u.getPort() < 0 ? 443 : u.getPort();
    }

    private String routeUrl(String route) {
        if (route == null || route.isEmpty()) route = "/";
        if (!route.startsWith("/")) route = "/" + route;
        return baseUrl + route;
    }

    private void openRoute(String route) {
        if (web != null) web.loadUrl(routeUrl(route));
    }

    private void openExternal(Uri uri) {
        try {
            startActivity(new Intent(Intent.ACTION_VIEW, uri));
        } catch (Exception e) {
            Toast.makeText(this, "Nie można otworzyć odnośnika.", Toast.LENGTH_SHORT).show();
        }
    }

    private void updateChrome(String current) {
        try {
            String p = Uri.parse(current).getPath();
            boolean auth = p != null && (
                p.endsWith("/login") ||
                p.endsWith("/mfa/challenge") ||
                p.endsWith("/password/forgot") ||
                p.endsWith("/password/reset")
            );
            bottom.setVisibility(auth ? View.GONE : View.VISIBLE);
        } catch (Exception ignored) {}
    }

    private void showMore() {
        String[] labels = {
            "Dostawcy", "Powierzenia danych", "Narzędzia AI", "Raporty SZBI",
            "Ewidencja wejść", "Analiza ryzyka", "Naruszenia RODO",
            "Zgłoszenia CSIRT / S46", "Audit Trail", "Centrum integralności",
            "Administracja", "Wyloguj"
        };
        String[] routes = {
            "/suppliers", "/processors", "/ai-tools", "/reports",
            "/entries", "/risk-analyses", "/gdpr-breaches",
            "/cyber-reports", "/audit", "/system-integrity",
            "/administration", "/logout"
        };
        new AlertDialog.Builder(this)
            .setTitle("Więcej")
            .setItems(labels, (d, which) -> openRoute(routes[which]))
            .show();
    }

    private void showSettings() {
        String[] items = {
            "Odśwież stronę",
            "Otwórz Dashboard",
            "Zmień adres serwera",
            "Wyczyść sesję i zaloguj ponownie",
            "Informacje o aplikacji"
        };
        new AlertDialog.Builder(this)
            .setTitle("Ustawienia")
            .setItems(items, (d, which) -> {
                if (which == 0) web.reload();
                else if (which == 1) openRoute("/");
                else if (which == 2) changeServer();
                else if (which == 3) clearSession();
                else showAbout();
            }).show();
    }

    private void changeServer() {
        EditText input = new EditText(this);
        input.setSingleLine(true);
        input.setText(baseUrl);
        input.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);

        new AlertDialog.Builder(this)
            .setTitle("Adres serwera")
            .setMessage("Zmiana adresu wyloguje bieżącą sesję. Dozwolone jest wyłącznie HTTPS.")
            .setView(input)
            .setNegativeButton("Anuluj", null)
            .setPositiveButton("Zapisz", (d, which) -> {
                String u = normalizeUrl(input.getText().toString());
                if (u == null) {
                    Toast.makeText(this, "Nieprawidłowy adres HTTPS.", Toast.LENGTH_LONG).show();
                    return;
                }
                CookieManager.getInstance().removeAllCookies(null);
                CookieManager.getInstance().flush();
                baseUrl = u;
                getSharedPreferences(PREFS, MODE_PRIVATE).edit().putString(PREF_URL, u).apply();
                openRoute("/");
            }).show();
    }

    private void clearSession() {
        CookieManager.getInstance().removeAllCookies(null);
        CookieManager.getInstance().flush();
        web.clearCache(true);
        openRoute("/login");
    }

    private void showAbout() {
        new AlertDialog.Builder(this)
            .setTitle("Cloud UM Przemyśl")
            .setMessage(
                "Aplikacja mobilna 1.0.0\n\n" +
                "Bezpieczny klient Android dla systemu Cloud. Logowanie, MFA, role i Audit Trail są obsługiwane przez system serwerowy.\n\n" +
                "Aplikacja wymaga HTTPS i nie przechowuje haseł."
            )
            .setPositiveButton("OK", null)
            .show();
    }

    private void download(String url, String userAgent, String contentDisposition, String mimeType) {
        Uri uri = Uri.parse(url);
        if (!isInternal(uri)) {
            openExternal(uri);
            return;
        }
        try {
            DownloadManager.Request request = new DownloadManager.Request(uri);
            String cookies = CookieManager.getInstance().getCookie(url);
            if (cookies != null) request.addRequestHeader("Cookie", cookies);
            if (userAgent != null) request.addRequestHeader("User-Agent", userAgent);
            if (mimeType != null) request.setMimeType(mimeType);
            String fileName = URLUtil.guessFileName(url, contentDisposition, mimeType);
            request.setTitle(fileName);
            request.setDescription("Pobieranie z systemu Cloud");
            request.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
            request.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, fileName);
            ((DownloadManager) getSystemService(Context.DOWNLOAD_SERVICE)).enqueue(request);
            Toast.makeText(this, "Rozpoczęto pobieranie.", Toast.LENGTH_SHORT).show();
        } catch (Exception e) {
            Toast.makeText(this, "Nie udało się pobrać pliku.", Toast.LENGTH_LONG).show();
        }
    }

    @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != FILE_CHOOSER || fileCallback == null) return;
        Uri[] result = null;
        if (resultCode == RESULT_OK && data != null) {
            if (data.getClipData() != null) {
                int count = data.getClipData().getItemCount();
                result = new Uri[count];
                for (int i = 0; i < count; i++) result[i] = data.getClipData().getItemAt(i).getUri();
            } else if (data.getData() != null) {
                result = new Uri[]{data.getData()};
            }
        }
        fileCallback.onReceiveValue(result);
        fileCallback = null;
    }

    @Override public void onBackPressed() {
        if (web != null && web.canGoBack()) {
            web.goBack();
        } else {
            new AlertDialog.Builder(this)
                .setTitle("Zamknąć aplikację?")
                .setNegativeButton("Nie", null)
                .setPositiveButton("Tak", (d, w) -> finish())
                .show();
        }
    }

    @Override protected void onDestroy() {
        if (web != null) {
            ViewParent parent = web.getParent();
            if (parent instanceof ViewGroup) ((ViewGroup) parent).removeView(web);
            web.stopLoading();
            web.setWebChromeClient(null);
            web.setWebViewClient(null);
            web.destroy();
        }
        super.onDestroy();
    }
}
