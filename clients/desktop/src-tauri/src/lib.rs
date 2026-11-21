#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    std::panic::set_hook(Box::new(|info| {
        let path = std::env::current_exe()
            .ok()
            .and_then(|p| p.parent().map(|d| d.join("desktop-crash.log")));
        if let Some(path) = path {
            let _ = std::fs::write(path, format!("{info}\n"));
        }
    }));
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("error while running Hoshinoumi desktop");
}
