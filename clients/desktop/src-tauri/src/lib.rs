#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // 当前 Windows/WebView2 环境在 GPU 合成初始化时崩溃，先禁用 GPU。
    std::env::set_var("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", "--disable-gpu");
    std::panic::set_hook(Box::new(|info| {
        if let Some(path) = std::env::current_exe().ok().and_then(|p| p.parent().map(|d| d.join("desktop-crash.log"))) {
            let _ = std::fs::write(path, format!("{info}\n"));
        }
    }));
    tauri::Builder::default()
        .setup(|app| {
            // 默认 WebView 数据目录在本机可能创建失败，显式使用用户可写目录。
            let base = std::env::var_os("LOCALAPPDATA")
                .map(std::path::PathBuf::from)
                .unwrap_or_else(|| std::env::current_dir().unwrap_or_default());
            let data = base.join("Hoshinoumi").join("webview");
            std::fs::create_dir_all(&data)?;
            tauri::WebviewWindowBuilder::new(app, "main", tauri::WebviewUrl::App("index.html".into()))
                .title("Hoshinoumi")
                .inner_size(1440.0, 900.0)
                .min_inner_size(1180.0, 760.0)
                .center()
                .decorations(false)
                .data_directory(data)
                .build()?;
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running Hoshinoumi desktop");
}
