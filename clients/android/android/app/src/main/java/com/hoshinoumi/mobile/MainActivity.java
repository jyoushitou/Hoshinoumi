package com.hoshinoumi.mobile;

import android.Manifest;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.os.Bundle;
import android.webkit.JavascriptInterface;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;

import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsControllerCompat;

import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    private PermissionRequest pendingWebPermission;

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

        getBridge().getWebView().addJavascriptInterface(new Object() {
            @JavascriptInterface
            public void openConfig() {
                runOnUiThread(() -> {
                    String base = getBridge().getLocalUrl();
                    if (base.endsWith("/")) base = base.substring(0, base.length() - 1);
                    getBridge().getWebView().loadUrl(base + "/index.html?config=1");
                });
            }
        }, "HoshinoumiConfig");
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
