use tauri::Manager;

struct ServerProcess(std::sync::Mutex<Option<std::process::Child>>);

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .manage(ServerProcess(std::sync::Mutex::new(None)))
        .setup(|app| {
            let server_exe = if cfg!(target_os = "windows") {
                "server.exe"
            } else {
                "server"
            };

            let server_path = if cfg!(debug_assertions) {
                std::env::current_dir()
                    .unwrap()
                    .parent()
                    .unwrap()
                    .join("src-tauri")
                    .join("server")
                    .join(server_exe)
            } else {
                std::env::current_exe()
                    .unwrap()
                    .parent()
                    .unwrap()
                    .join("server")
                    .join(server_exe)
            };

            println!("[SERVER] path: {:?}", server_path);

            let child = std::process::Command::new(&server_path)
                .current_dir(server_path.parent().unwrap())
                .spawn()
                .expect("no se pudo lanzar el servidor Python");

            *app.state::<ServerProcess>().0.lock().unwrap() = Some(child);
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                let state = window.state::<ServerProcess>();
                let child = state.0.lock().unwrap().take();
                if let Some(mut process) = child {
                    let _ = process.kill();
                    println!("[SERVER] Proceso terminado");
                };
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}