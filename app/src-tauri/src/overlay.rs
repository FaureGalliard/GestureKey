//! The feedback overlay: a transparent, click-through, always-on-top strip
//! that shows gesture toasts and hold progress at the top of the screen.

use tauri::{AppHandle, Manager, PhysicalPosition, WebviewWindow};

const LABEL: &str = "overlay";
const TOP_MARGIN: f64 = 18.0; // logical px from the top of the monitor

pub fn setup(app: &AppHandle) {
    if let Some(win) = app.get_webview_window(LABEL) {
        let _ = win.set_ignore_cursor_events(true);
        let _ = place(&win, app);
    }
}

/// Top-centre of the monitor under the cursor (works across multiple monitors).
fn place(win: &WebviewWindow, app: &AppHandle) -> tauri::Result<()> {
    let cursor = app.cursor_position()?;
    let monitors = win.available_monitors()?;
    let monitor = monitors
        .iter()
        .find(|m| {
            let (p, s) = (m.position(), m.size());
            cursor.x >= p.x as f64
                && cursor.x < (p.x + s.width as i32) as f64
                && cursor.y >= p.y as f64
                && cursor.y < (p.y + s.height as i32) as f64
        })
        .cloned()
        .or(win.primary_monitor()?);
    let Some(monitor) = monitor else { return Ok(()) };

    let size = win.outer_size()?;
    let (p, s) = (monitor.position(), monitor.size());
    let x = p.x + (s.width as i32 - size.width as i32) / 2;
    let y = p.y + (TOP_MARGIN * monitor.scale_factor()) as i32;
    win.set_position(PhysicalPosition::new(x, y))
}

/// Called by the overlay right before it shows something.
#[tauri::command]
pub fn overlay_place(app: AppHandle) -> Result<(), String> {
    let win = app.get_webview_window(LABEL).ok_or("overlay window missing")?;
    place(&win, &app).map_err(|e| e.to_string())
}
