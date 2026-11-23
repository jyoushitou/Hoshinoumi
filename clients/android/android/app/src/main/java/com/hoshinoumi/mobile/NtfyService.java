package com.hoshinoumi.mobile;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.IBinder;

import androidx.core.app.NotificationCompat;
import androidx.core.content.ContextCompat;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

public class NtfyService extends Service {
    public static final String CHANNEL_ID = "hoshinoumi_push";
    public static final String EXTRA_BACKEND = "backend";
    public static final String EXTRA_SERVER = "ntfy_server";
    public static final String EXTRA_TOPIC = "ntfy_topic";
    public static final int FOREGROUND_ID = 1001;
    private volatile boolean running = false;
    private Thread worker;
    private String server;
    private String topic;

    @Override
    public void onCreate() {
        super.onCreate();
        NotificationManager manager = getSystemService(NotificationManager.class);
        if (manager != null) {
            NotificationChannel channel = new NotificationChannel(CHANNEL_ID, "Hoshinoumi 消息", NotificationManager.IMPORTANCE_DEFAULT);
            channel.setDescription("聊天消息与提醒");
            manager.createNotificationChannel(channel);
        }
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent == null) return START_NOT_STICKY;
        String action = intent.getAction();
        if ("STOP".equals(action)) {
            stopSelf();
            return START_NOT_STICKY;
        }
        server = trimSlash(intent.getStringExtra(EXTRA_SERVER));
        topic = intent.getStringExtra(EXTRA_TOPIC);
        if (server == null || server.isEmpty() || topic == null || topic.isEmpty()) {
            stopSelf();
            return START_NOT_STICKY;
        }
        startForeground(FOREGROUND_ID, foregroundNotification());
        if (worker == null || !worker.isAlive()) {
            running = true;
            worker = new Thread(this::listenLoop, "hoshinoumi-ntfy");
            worker.start();
        }
        return START_STICKY;
    }

    private Notification foregroundNotification() {
        Intent open = new Intent(this, MainActivity.class);
        PendingIntent pending = PendingIntent.getActivity(this, 0, open, PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
        return new NotificationCompat.Builder(this, CHANNEL_ID)
                .setSmallIcon(R.drawable.ic_notification)
                .setContentTitle("Hoshinoumi 通知已开启")
                .setContentText("后台接收消息中")
                .setOngoing(true)
                .setPriority(NotificationCompat.PRIORITY_LOW)
                .setContentIntent(pending)
                .build();
    }

    private void listenLoop() {
        while (running) {
            HttpURLConnection connection = null;
            try {
                URL url = new URL(server + "/" + topic + "/sse");
                connection = (HttpURLConnection) url.openConnection();
                connection.setConnectTimeout(15000);
                connection.setReadTimeout(0);
                connection.setRequestProperty("Accept", "text/event-stream");
                connection.setRequestProperty("Cache-Control", "no-cache");
                int code = connection.getResponseCode();
                if (code < 200 || code >= 300) throw new IllegalStateException("ntfy HTTP " + code);
                try (BufferedReader reader = new BufferedReader(new InputStreamReader(connection.getInputStream(), StandardCharsets.UTF_8))) {
                    StringBuilder data = new StringBuilder();
                    String line;
                    while (running && (line = reader.readLine()) != null) {
                        if (line.startsWith("data:")) {
                            data.append(line.substring(5).trim());
                        } else if (line.isEmpty() && data.length() > 0) {
                            handlePayload(data.toString());
                            data.setLength(0);
                        }
                    }
                }
            } catch (Exception ignored) {
                if (!running) break;
                try { Thread.sleep(5000); } catch (InterruptedException e) { Thread.currentThread().interrupt(); break; }
            } finally {
                if (connection != null) connection.disconnect();
            }
        }
    }

    private void handlePayload(String raw) {
        try {
            JSONObject json = new JSONObject(raw);
            String event = json.optString("event", "message");
            if (!"message".equals(event)) return;
            String title = json.optString("title", "Hoshinoumi");
            String message = json.optString("message", "");
            if (message.isEmpty()) return;
            String click = json.optString("click", "/chat");
            showNotification(title, message, click);
        } catch (Exception ignored) {
        }
    }

    private void showNotification(String title, String message, String deepLink) {
        if (ContextCompat.checkSelfPermission(this, "android.permission.POST_NOTIFICATIONS") != PackageManager.PERMISSION_GRANTED
                && android.os.Build.VERSION.SDK_INT >= 33) return;
        Intent open = new Intent(this, MainActivity.class);
        open.putExtra("deep_link", deepLink);
        open.setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        PendingIntent pending = PendingIntent.getActivity(this, (int) (System.currentTimeMillis() & 0xffff), open, PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
        Notification notification = new NotificationCompat.Builder(this, CHANNEL_ID)
                .setSmallIcon(R.drawable.ic_notification)
                .setContentTitle(title)
                .setContentText(message)
                .setStyle(new NotificationCompat.BigTextStyle().bigText(message))
                .setAutoCancel(true)
                .setContentIntent(pending)
                .build();
        NotificationManager manager = getSystemService(NotificationManager.class);
        if (manager != null) manager.notify((int) (System.currentTimeMillis() & 0xffff), notification);
        Intent refresh = new Intent("com.hoshinoumi.PUSH_RECEIVED");
        refresh.setPackage(getPackageName());
        sendBroadcast(refresh);
    }

    private static String trimSlash(String value) {
        if (value == null) return "";
        while (value.endsWith("/")) value = value.substring(0, value.length() - 1);
        return value;
    }

    @Override
    public void onDestroy() {
        running = false;
        if (worker != null) worker.interrupt();
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
