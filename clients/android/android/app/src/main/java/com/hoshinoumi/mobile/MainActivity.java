package com.hoshinoumi.mobile;

import android.Manifest;
import android.app.DownloadManager;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.database.Cursor;
import android.provider.Settings;
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

public class MainActivity extends BridgeActivity {
    private PermissionRequest pendingWebPermission;
    private long updateDownloadId = -1;
    private BroadcastReceiver updateReceiver;

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

    @Override
    public void onBackPressed() {
        try {
            WebView webView = getBridge().getWebView();
            if (webView != null && webView.canGoBack()) {
                webView.goBack();
                return;
            }
        } catch (Exception ignored) {
        }
        super.onBackPressed();
    }

    @Override
    public void onDestroy() {
        if (updateReceiver != null) {
            try { unregisterReceiver(updateReceiver); } catch (Exception ignored) { }
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
