//! Spawns and owns the Python engine (the "sidecar").
//!
//! - dev (debug build): runs `engine/.venv` Python directly — not `uv run`,
//!   which would leave the Python child alive when uv is killed.
//! - release: runs the PyInstaller build bundled under `resources/engine/`.
//! - `GESTUREKEY_NO_ENGINE=1`: spawn nothing; run `pnpm engine` yourself.
//!
//! The engine also gets `--parent-pid` and exits by itself if we die.

use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::Mutex;

use tauri::{AppHandle, Manager};

pub const PORT: u16 = 8765;

#[derive(Default)]
pub struct EngineProcess(Mutex<Option<Child>>);

fn command(app: &AppHandle) -> Result<Command, String> {
    let mut cmd = if cfg!(debug_assertions) {
        let engine_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../engine");
        let python = if cfg!(windows) {
            engine_dir.join(".venv/Scripts/python.exe")
        } else {
            engine_dir.join(".venv/bin/python")
        };
        if !python.exists() {
            return Err(format!(
                "no existe {} — corre `uv sync` en engine/",
                python.display()
            ));
        }
        let mut cmd = Command::new(python);
        cmd.args(["-m", "gesturekey"]).current_dir(engine_dir);
        cmd
    } else {
        let exe = if cfg!(windows) { "gesturekey-engine.exe" } else { "gesturekey-engine" };
        let path = app
            .path()
            .resource_dir()
            .map_err(|e| e.to_string())?
            .join("engine/gesturekey-engine")
            .join(exe);
        let mut cmd = Command::new(&path);
        cmd.current_dir(path.parent().unwrap_or(&path));
        cmd
    };

    cmd.args(["--port", &PORT.to_string(), "--parent-pid", &std::process::id().to_string()]);

    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        cmd.creation_flags(CREATE_NO_WINDOW);
    }
    Ok(cmd)
}

pub fn spawn(app: &AppHandle) -> Result<(), String> {
    if std::env::var_os("GESTUREKEY_NO_ENGINE").is_some() {
        println!("[ENGINE] GESTUREKEY_NO_ENGINE set — not spawning");
        return Ok(());
    }
    let child = command(app)?.spawn().map_err(|e| format!("no se pudo lanzar el motor: {e}"))?;
    println!("[ENGINE] pid {}", child.id());
    *app.state::<EngineProcess>().0.lock().unwrap() = Some(child);
    Ok(())
}

pub fn kill(app: &AppHandle) {
    if let Some(mut child) = app.state::<EngineProcess>().0.lock().unwrap().take() {
        let _ = child.kill();
        let _ = child.wait();
    }
}
