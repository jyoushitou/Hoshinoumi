package com.hoshinoumi.mobile;

import android.animation.ObjectAnimator;
import android.animation.ValueAnimator;
import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.view.animation.DecelerateInterpolator;

public class SplashActivity extends Activity {
    private final Handler handler = new Handler(Looper.getMainLooper());

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        Window window = getWindow();
        window.addFlags(WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS);
        window.setStatusBarColor(0xFF07101F);
        window.setNavigationBarColor(0xFF07101F);
        window.getDecorView().setSystemUiVisibility(0);
        setContentView(R.layout.activity_splash);

        View logo = findViewById(R.id.splashLogo);
        ObjectAnimator floatAnim = ObjectAnimator.ofFloat(logo, "translationY", 0f, -8f);
        floatAnim.setDuration(1400);
        floatAnim.setRepeatMode(ValueAnimator.REVERSE);
        floatAnim.setRepeatCount(ValueAnimator.INFINITE);
        floatAnim.setInterpolator(new DecelerateInterpolator());
        floatAnim.start();

        View bar = findViewById(R.id.splashBar);
        ObjectAnimator barAnim = ObjectAnimator.ofFloat(bar, "translationX", -72f, 160f);
        barAnim.setDuration(1200);
        barAnim.setRepeatCount(ValueAnimator.INFINITE);
        barAnim.setInterpolator(new DecelerateInterpolator());
        barAnim.start();

        handler.postDelayed(this::enterApp, 2200);
    }

    private void enterApp() {
        Intent intent = new Intent(this, MainActivity.class);
        if (getIntent() != null && getIntent().getExtras() != null) {
            intent.putExtras(getIntent());
        }
        startActivity(intent);
        overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out);
        finish();
    }

    @Override
    protected void onDestroy() {
        handler.removeCallbacksAndMessages(null);
        super.onDestroy();
    }
}
