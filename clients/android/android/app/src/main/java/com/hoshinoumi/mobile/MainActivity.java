package com.hoshinoumi.mobile;

import android.graphics.Color;
import android.os.Bundle;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;

import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsControllerCompat;

import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
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
}
