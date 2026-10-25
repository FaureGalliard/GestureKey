mod engine;
mod overlay;

use tauri::{
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    Manager, RunEvent, WindowEvent,
};

use engine::EngineProcess;

fn show_main(app: &tauri::AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.show();
        let _ = window.unminimize();
        let _ = window.set_focus();
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
        .manage(EngineProcess::default())
        .invoke_handler(tauri::generate_handler![overlay::overlay_place])
        .setup(|app| {
            if let Err(err) = engine::spawn(app.handle()) {
                eprintln!("[ENGINE] {err}");
            }
            overlay::setup(app.handle());

            let show = MenuItem::with_id(app, "show", "Mostrar", true, None::<&str>)?;
            let quit = MenuItem::with_id(app, "quit", "Salir", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&show, &quit])?;

            TrayIconBuilder::with_id("main")
                .icon(app.default_window_icon().cloned().expect("bundle icon"))
                .tooltip("GestureKey")
                .menu(&menu)
                .show_menu_on_left_click(false)
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "show" => show_main(app),
                    "quit" => app.exit(0),
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = event
                    {
                        show_main(tray.app_handle());
                    }
                })
                .build(app)?;
            Ok(())
        })
        .on_window_event(|window, event| {
            // Closing the window keeps GestureKey running in the tray.
            if let ("main", WindowEvent::CloseRequested { api, .. }) = (window.label(), event) {
                api.prevent_close();
                let _ = window.hide();
            }
        })
        .build(tauri::generate_context!())
        .expect("error while building GestureKey");

    app.run(|app, event| {
        if let RunEvent::Exit = event {
            engine::kill(app);
        }
    });
}
