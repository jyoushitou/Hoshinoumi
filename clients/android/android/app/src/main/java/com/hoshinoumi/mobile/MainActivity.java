package com.hoshinoumi.mobile;

import android.os.Bundle;
import android.webkit.JavascriptInterface;

import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
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
