package com.hoshinoumi.mobile;

import android.Manifest;
import android.app.DownloadManager;
import android.content.BroadcastReceiver;
import android.content.ComponentCallbacks2;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.os.SystemClock;
import android.database.Cursor;
import android.provider.Settings;
import android.provider.Settings.Secure;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.os.Bundle;
import android.webkit.CookieManager;
import android.webkit.JavascriptInterface;
import android.webkit.URLUtil;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.widget.Toast;

import androidx.core.app.ActivityCompat;
import androidx.core.app.NotificationManagerCompat;
import androidx.core.content.ContextCompat;
import androidx.core.content.FileProvider;

import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsControllerCompat;

import com.getcapacitor.BridgeActivity;

import org.json.JSONObject;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

public class MainActivity extends BridgeActivity {
    private PermissionRequest pendingWebPermission;
    private long updateDownloadId = -1;
    private BroadcastReceiver updateReceiver;
    private BroadcastReceiver pushRefreshReceiver;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(Color.parseColor("#F7FAFF"));
        getWindow().setNavigationBarColor(Color.parseColor("#F7FAFF"));
        WindowInsetsControllerCompat controller = WindowCompat.getInsetsController(getWindow(), getWindow().getDecorView());
        controller.setAppearanceLightStatusBars(true);
        controller.setAppearanceLightNavigationBars(true);

        WebSettings settings = getBridge().getWebView().getSettings();
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(true);
        settings.setMixedContentMode(2); // WebSettings.MIXED_CONTENT_NEVER
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setLoadsImagesAutomatically(true);
        settings.setBlockNetworkImage(false);
        boolean debuggable = (getApplicationInfo().flags & android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE) != 0;
        if (!debuggable) WebView.setWebContentsDebuggingEnabled(false);
        settings.setSafeBrowsingEnabled(true);
        settings.setJavaScriptCanOpenWindowsAutomatically(false);
        settings.setSupportMultipleWindows(false);
        settings.setMediaPlaybackRequiresUserGesture(true);
        getBridge().getWebView().setBackgroundColor(Color.parseColor("#F7FAFF"));

        getBridge().getWebView().setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(PermissionRequest request) {
                String[] resources = request.getResources();
                boolean needCamera = false;
                boolean needMic = false;
                for (String resource : resources) {
                    if (PermissionRequest.RESOURCE_VIDEO_CAPTURE.equals(resource)) needCamera = true;
                    if (PermissionRequest.RESOURCE_AUDIO_CAPTURE.equals(resource)) needMic = true;
                }
                java.util.ArrayList<String> missing = new java.util.ArrayList<>();
                if (needCamera && ContextCompat.checkSelfPermission(MainActivity.this, Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) missing.add(Manifest.permission.CAMERA);
                if (needMic && ContextCompat.checkSelfPermission(MainActivity.this, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) missing.add(Manifest.permission.RECORD_AUDIO);
                if (missing.isEmpty()) {
                    request.grant(resources);
                } else {
                    pendingWebPermission = request;
                    ActivityCompat.requestPermissions(MainActivity.this, missing.toArray(new String[0]), 4102);
                }
            }
        });

        getBridge().getWebView().setDownloadListener((url, userAgent, contentDisposition, mimeType, contentLength) -> {
            try {
                String fileName = URLUtil.guessFileName(url, contentDisposition, mimeType);
                DownloadManager.Request request = new DownloadManager.Request(Uri.parse(url));
                request.setMimeType(mimeType);
                request.addRequestHeader("User-Agent", userAgent);
                String cookie = CookieManager.getInstance().getCookie(url);
                if (cookie != null) request.addRequestHeader("Cookie", cookie);
                request.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
                request.setDestinationInExternalFilesDir(this, Environment.DIRECTORY_DOWNLOADS, fileName);
                DownloadManager manager = (DownloadManager) getSystemService(DOWNLOAD_SERVICE);
                if (manager != null) {
                    manager.enqueue(request);
                    Toast.makeText(this, "开始下载：" + fileName, Toast.LENGTH_SHORT).show();
                }
            } catch (Exception e) {
                Toast.makeText(this, "下载失败：" + e.getMessage(), Toast.LENGTH_LONG).show();
            }
        });

        updateReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {
                if (DownloadManager.ACTION_DOWNLOAD_COMPLETE.equals(intent.getAction())) {
                    long id = intent.getLongExtra(DownloadManager.EXTRA_DOWNLOAD_ID, -1);
                    if (id == updateDownloadId) installDownloadedApk(id);
                }
            }
        };
        ContextCompat.registerReceiver(this, updateReceiver, new IntentFilter(DownloadManager.ACTION_DOWNLOAD_COMPLETE), ContextCompat.RECEIVER_NOT_EXPORTED);

        pushRefreshReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {
                try {
                    getBridge().getWebView().evaluateJavascript("window.dispatchEvent(new CustomEvent('hoshinoumi:push'))", null);
                } catch (Exception ignored) {
                }
            }
        };
        ContextCompat.registerReceiver(this, pushRefreshReceiver, new IntentFilter("com.hoshinoumi.PUSH_RECEIVED"), ContextCompat.RECEIVER_NOT_EXPORTED);

        getBridge().getWebView().addJavascriptInterface(new Object() {
            @JavascriptInterface
            public void openConfig() {
                runOnUiThread(() -> {
                    String base = getBridge().getLocalUrl();
                    if (base.endsWith("/")) base = base.substring(0, base.length() - 1);
                    getBridge().getWebView().loadUrl(base + "/index.html?config=1");
                });
            }
            private boolean granted(String permission) {
                return ContextCompat.checkSelfPermission(MainActivity.this, permission) == PackageManager.PERMISSION_GRANTED;
            }

            @JavascriptInterface
            public void downloadApk(String url) {
                runOnUiThread(() -> {
                    try {
                        DownloadManager.Request request = new DownloadManager.Request(Uri.parse(url));
                        request.setMimeType("application/vnd.android.package-archive");
                        request.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
                        request.setDestinationInExternalFilesDir(MainActivity.this, Environment.DIRECTORY_DOWNLOADS, "hoshinoumi-update.apk");
                        DownloadManager manager = (DownloadManager) getSystemService(DOWNLOAD_SERVICE);
                        if (manager == null) throw new IllegalStateException("DownloadManager unavailable");
                        updateDownloadId = manager.enqueue(request);
                        Toast.makeText(MainActivity.this, "正在下载更新…", Toast.LENGTH_SHORT).show();
                    } catch (Exception e) {
                        Toast.makeText(MainActivity.this, "更新下载失败：" + e.getMessage(), Toast.LENGTH_LONG).show();
                    }
                });
            }

            @JavascriptInterface
            public String getDownloadStatus() {
                JSONObject o = new JSONObject();
                try {
                    o.put("status", updateDownloadId < 0 ? "none" : "downloading");
                    if (updateDownloadId >= 0) {
                        DownloadManager manager = (DownloadManager) getSystemService(DOWNLOAD_SERVICE);
                        if (manager != null) {
                            try (android.database.Cursor c = manager.query(new DownloadManager.Query().setFilterById(updateDownloadId))) {
                                if (c != null && c.moveToFirst()) {
                                    int status = c.getInt(c.getColumnIndexOrThrow(DownloadManager.COLUMN_STATUS));
                                    long done = c.getLong(c.getColumnIndexOrThrow(DownloadManager.COLUMN_BYTES_DOWNLOADED_SO_FAR));
                                    long total = c.getLong(c.getColumnIndexOrThrow(DownloadManager.COLUMN_TOTAL_SIZE_BYTES));
                                    o.put("status", status == DownloadManager.STATUS_SUCCESSFUL ? "complete" : status == DownloadManager.STATUS_FAILED ? "failed" : "downloading");
                                    o.put("downloaded", done);
                                    o.put("total", total);
                                    if (status == DownloadManager.STATUS_FAILED) o.put("reason", c.getInt(c.getColumnIndexOrThrow(DownloadManager.COLUMN_REASON)));
                                }
                            }
                        }
                    }
                } catch (Exception e) {
                    try { o.put("status", "failed"); o.put("reason", e.getMessage()); } catch (Exception ignored) { }
                }
                return o.toString();
            }

            @JavascriptInterface
            public String getEnvironment() {
                JSONObject o = new JSONObject();
                try {
                    android.content.pm.PackageInfo info = getPackageManager().getPackageInfo("com.google.android.webview", 0);
                    o.put("webview", info.versionName);
                } catch (Exception e) {
                    try {
                        android.content.pm.PackageInfo info = getPackageManager().getPackageInfo("com.android.webview", 0);
                        o.put("webview", info.versionName);
                    } catch (Exception ignored) {
                        try { o.put("webview", ""); } catch (Exception ignored2) { }
                    }
                }
                try {
                    android.content.pm.PackageInfo app = getPackageManager().getPackageInfo(getPackageName(), 0);
                    o.put("appVersion", app.versionName);
                    o.put("versionCode", app.versionCode);
                } catch (Exception ignored) {
                }
                try {
                    o.put("sdk", Build.VERSION.SDK_INT);
                    o.put("android", Build.VERSION.RELEASE);
                    o.put("model", Build.MODEL);
                } catch (Exception ignored) {
                }
                return o.toString();
            }

            @JavascriptInterface
            public String getPermissionStatus() {
                JSONObject o = new JSONObject();
                try {
                    o.put("notifications", NotificationManagerCompat.from(MainActivity.this).areNotificationsEnabled());
                    o.put("camera", granted(Manifest.permission.CAMERA));
                    o.put("microphone", granted(Manifest.permission.RECORD_AUDIO));
                    if (Build.VERSION.SDK_INT >= 33) o.put("photos", granted(Manifest.permission.READ_MEDIA_IMAGES));
                    else o.put("photos", granted(Manifest.permission.READ_EXTERNAL_STORAGE));
                    o.put("android", Build.VERSION.RELEASE);
                    o.put("sdk", Build.VERSION.SDK_INT);
                } catch (Exception ignored) {
                }
                return o.toString();
            }

            @JavascriptInterface
            public void requestPermission(String key) {
                runOnUiThread(() -> {
                    if ("camera".equals(key)) {
                        ActivityCompat.requestPermissions(MainActivity.this, new String[]{Manifest.permission.CAMERA}, 4201);
                    } else if ("microphone".equals(key)) {
                        ActivityCompat.requestPermissions(MainActivity.this, new String[]{Manifest.permission.RECORD_AUDIO}, 4202);
                    } else if ("photos".equals(key)) {
                        String perm = Build.VERSION.SDK_INT >= 33 ? Manifest.permission.READ_MEDIA_IMAGES : Manifest.permission.READ_EXTERNAL_STORAGE;
                        ActivityCompat.requestPermissions(MainActivity.this, new String[]{perm}, 4203);
                    } else if ("notifications".equals(key) && Build.VERSION.SDK_INT >= 33) {
                        ActivityCompat.requestPermissions(MainActivity.this, new String[]{"android.permission.POST_NOTIFICATIONS"}, 4204);
                    } else {
                        openAppSettings();
                    }
                });
            }

            @JavascriptInterface
            public void openUrl(String url) {
                runOnUiThread(() -> {
                    try {
                        startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url)));
                    } catch (Exception ignored) {
                    }
                });
            }

            @JavascriptInterface
            public void openAppSettings() {
                runOnUiThread(() -> {
                    Intent intent = new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:" + getPackageName()));
                    startActivity(intent);
                });
            }

            @JavascriptInterface
            public void openBatterySettings() {
                runOnUiThread(() -> {
                    Intent intent = new Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS);
                    try { startActivity(intent); } catch (Exception e) { openAppSettings(); }
                });
            }

            @JavascriptInterface
            public void openAutostartSettings() {
                runOnUiThread(() -> {
                    try {
                        Intent intent = new Intent();
                        intent.setClassName("com.miui.securitycenter", "com.miui.permcenter.autostart.AutoStartManagementActivity");
                        startActivity(intent);
                    } catch (Exception e) {
                        openAppSettings();
                    }
                });
            }

            @JavascriptInterface
            public void shareText(String text) {
                runOnUiThread(() -> {
                    Intent send = new Intent(Intent.ACTION_SEND);
                    send.setType("text/plain");
                    send.putExtra(Intent.EXTRA_TEXT, text == null ? "" : text);
                    startActivity(Intent.createChooser(send, "分享"));
                });
            }
            @JavascriptInterface
            public void startPush(String backendUrl, String token, String ntfyServer) {
                runOnUiThread(() -> {
                    if (Build.VERSION.SDK_INT >= 33 && ContextCompat.checkSelfPermission(MainActivity.this, "android.permission.POST_NOTIFICATIONS") != PackageManager.PERMISSION_GRANTED) {
                        ActivityCompat.requestPermissions(MainActivity.this, new String[]{"android.permission.POST_NOTIFICATIONS"}, 4301);
                    }
                });
                SharedPreferences prefs = getSharedPreferences("hoshinoumi_push", MODE_PRIVATE);
                String androidId = Secure.getString(getContentResolver(), Secure.ANDROID_ID);
                String topic = prefs.getString("topic", "");
                if (topic == null || topic.isEmpty()) topic = "hoshinoumi-" + (androidId == null ? "device" : androidId.toLowerCase());
                final String finalTopic = topic;
                final String backend = trimSlash(backendUrl);
                final String server = trimSlash(ntfyServer);
                final String finalToken = token == null ? "" : token;
                prefs.edit().putString("backend", backend).putString("server", server).putString("topic", finalTopic).putLong("last_seen", System.currentTimeMillis()).apply();
                new Thread(() -> {
                    boolean registered = false;
                    String deviceId = "";
                    try {
                        JSONObject payload = new JSONObject();
                        payload.put("platform", "android");
                        payload.put("topic", finalTopic);
                        payload.put("endpoint", server + "/" + finalTopic);
                        HttpURLConnection conn = (HttpURLConnection) new URL(backend + "/api/push/devices").openConnection();
                        conn.setRequestMethod("POST");
                        conn.setConnectTimeout(8000);
                        conn.setReadTimeout(8000);
                        conn.setDoOutput(true);
                        conn.setRequestProperty("Content-Type", "application/json");
                        if (!finalToken.isEmpty()) conn.setRequestProperty("Authorization", "Bearer " + finalToken);
                        try (OutputStream out = conn.getOutputStream()) {
                            out.write(payload.toString().getBytes(StandardCharsets.UTF_8));
                        }
                        int code = conn.getResponseCode();
                        if (code >= 200 && code < 300) {
                            registered = true;
                            java.io.InputStream stream = conn.getInputStream();
                            String text = new java.util.Scanner(stream, "UTF-8").useDelimiter("\\A").next();
                            JSONObject response = new JSONObject(text);
                            deviceId = response.optJSONObject("data") != null ? response.optJSONObject("data").optString("id", "") : "";
                        }
                    } catch (Exception ignored) {
                    }
                    prefs.edit().putBoolean("registered", registered).putString("device_id", deviceId).apply();
                    Intent service = new Intent(MainActivity.this, NtfyService.class);
                    service.setAction("START");
                    service.putExtra(NtfyService.EXTRA_BACKEND, backend);
                    service.putExtra(NtfyService.EXTRA_SERVER, server);
                    service.putExtra(NtfyService.EXTRA_TOPIC, finalTopic);
                    try {
                        ContextCompat.startForegroundService(MainActivity.this, service);
                    } catch (Exception ignored) {
                    }
                    final boolean wasRegistered = registered;
                    runOnUiThread(() -> Toast.makeText(MainActivity.this, wasRegistered ? "推送已注册，测试消息约 5 分钟后到达" : "推送服务已启动，但后端注册失败", Toast.LENGTH_LONG).show());
                }).start();
            }

            @JavascriptInterface
            public void stopPush() {
                stopService(new Intent(MainActivity.this, NtfyService.class));
                getSharedPreferences("hoshinoumi_push", MODE_PRIVATE).edit().putBoolean("registered", false).apply();
            }

            @JavascriptInterface
            public String getPushState() {
                SharedPreferences prefs = getSharedPreferences("hoshinoumi_push", MODE_PRIVATE);
                JSONObject o = new JSONObject();
                try {
                    o.put("registered", prefs.getBoolean("registered", false));
                    o.put("topic", prefs.getString("topic", ""));
                    o.put("server", prefs.getString("server", ""));
                    o.put("deviceId", prefs.getString("device_id", ""));
                } catch (Exception ignored) {
                }
                return o.toString();
            }

        }, "HoshinoumiConfig");
    }

    private void installDownloadedApk(long id) {
        DownloadManager manager = (DownloadManager) getSystemService(DOWNLOAD_SERVICE);
        if (manager == null) return;
        DownloadManager.Query query = new DownloadManager.Query().setFilterById(id);
        try (Cursor cursor = manager.query(query)) {
            if (cursor == null || !cursor.moveToFirst()) return;
            int status = cursor.getInt(cursor.getColumnIndexOrThrow(DownloadManager.COLUMN_STATUS));
            if (status != DownloadManager.STATUS_SUCCESSFUL) {
                Toast.makeText(this, "更新下载失败，已保留旧版本", Toast.LENGTH_LONG).show();
                return;
            }
            String local = cursor.getString(cursor.getColumnIndexOrThrow(DownloadManager.COLUMN_LOCAL_URI));
            Uri fileUri = FileProvider.getUriForFile(this, getPackageName() + ".fileprovider", new java.io.File(Uri.parse(local).getPath()));
            Intent install = new Intent(Intent.ACTION_VIEW);
            install.setDataAndType(fileUri, "application/vnd.android.package-archive");
            install.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(install);
        } catch (Exception e) {
            Toast.makeText(this, "无法启动安装器：" + e.getMessage(), Toast.LENGTH_LONG).show();
        }
    }

    private static String trimSlash(String value) {
        if (value == null) return "";
        while (value.endsWith("/")) value = value.substring(0, value.length() - 1);
        return value;
    }

    private void handleDeepLink(Intent intent) {
        if (intent == null) return;
        String link = intent.getStringExtra("deep_link");
        if (link == null || link.isEmpty()) return;
        String backend = getSharedPreferences("hoshinoumi_push", MODE_PRIVATE).getString("backend", "");
        if (backend == null || backend.isEmpty()) return;
        final String target = trimSlash(backend) + (link.startsWith("/") ? link : "/" + link);
        intent.removeExtra("deep_link");
        getBridge().getWebView().postDelayed(() -> getBridge().getWebView().loadUrl(target), 700);
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        handleDeepLink(intent);
    }

    private boolean backPending = false;
    private long lastMainBackAt = 0;

    @Override
    public void onBackPressed() {
        if (backPending) return;
        WebView webView;
        try {
            webView = getBridge().getWebView();
        } catch (Exception e) {
            finish();
            return;
        }
        if (webView == null) {
            finish();
            return;
        }
        backPending = true;
        webView.evaluateJavascript("(function(){try{return window.__hoshinoumiBack?String(window.__hoshinoumiBack()):'main'}catch(e){return 'main'}})()", value -> {
            backPending = false;
            String decision = value == null ? "" : value.replace("\"", "");
            if ("handled".equals(decision)) {
                lastMainBackAt = 0;
                return;
            }
            if ("main".equals(decision)) {
                long now = SystemClock.elapsedRealtime();
                if (lastMainBackAt > 0 && now - lastMainBackAt <= 2000) {
                    finish();
                } else {
                    lastMainBackAt = now;
                    Toast.makeText(MainActivity.this, "再滑一次退出应用", Toast.LENGTH_SHORT).show();
                }
                return;
            }
            finish();
        });
    }


    @Override
    public void onTrimMemory(int level) {
        super.onTrimMemory(level);
        if (level >= ComponentCallbacks2.TRIM_MEMORY_RUNNING_LOW) {
            try {
                WebView webView = getBridge().getWebView();
                webView.freeMemory();
                webView.clearCache(false);
            } catch (Exception ignored) { }
        }
    }

    @Override
    public void onLowMemory() {
        super.onLowMemory();
        try {
            WebView webView = getBridge().getWebView();
            webView.freeMemory();
            webView.clearCache(true);
        } catch (Exception ignored) { }
    }

    @Override
    public void onDestroy() {
        if (updateReceiver != null) {
            try { unregisterReceiver(updateReceiver); } catch (Exception ignored) { }
        }
        if (pushRefreshReceiver != null) {
            try { unregisterReceiver(pushRefreshReceiver); } catch (Exception ignored) { }
        }
        super.onDestroy();
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode != 4102 || pendingWebPermission == null) return;
        boolean granted = grantResults.length > 0;
        for (int result : grantResults) if (result != PackageManager.PERMISSION_GRANTED) granted = false;
        if (granted) pendingWebPermission.grant(pendingWebPermission.getResources());
        else pendingWebPermission.deny();
        pendingWebPermission = null;
    }
}
