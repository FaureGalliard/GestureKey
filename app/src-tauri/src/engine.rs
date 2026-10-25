//! Spawns and owns the Python engine (the "sidecar").
//!
//! - dev (debug build): runs `engine/.venv` Python directly — not `uv run`,
//!   which would leave the Python child alive when uv is killed.
//! - release: runs the PyInstaller build bundled under `resources/engine/`.
//! - `GESTUREKEY_NO_ENGINE=1`: spawn nothing; run `pnpm engine` yourself.
//!
//! The engine also gets `--parent-pid` and exits by itself if we die.

use std::io::{BufRead, BufReader, Read};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::{Duration, Instant};

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
    // Pipe the engine's output instead of inheriting it: with CREATE_NO_WINDOW an inherited
    // console handle is invalid in the child and its first print fails with EBADF.
    let mut child = command(app)?
        .stdin(Stdio::piped()) // closing it asks the engine to shut down cleanly
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("no se pudo lanzar el motor: {e}"))?;
    println!("[ENGINE] pid {}", child.id());
    if let Some(out) = child.stdout.take() {
        forward(out);
    }
    if let Some(err) = child.stderr.take() {
        forward(err);
    }
    *app.state::<EngineProcess>().0.lock().unwrap() = Some(child);
    Ok(())
}

/// Copy the engine's output lines to ours (visible in the `tauri dev` terminal).
fn forward(stream: impl Read + Send + 'static) {
    std::thread::spawn(move || {
        for line in BufReader::new(stream).lines().map_while(Result::ok) {
            println!("[py] {line}");
        }
    });
}

/// Graceful first (close stdin → the engine releases the camera and the recording;
/// measured ~2.3 s including interpreter teardown),
/// kill only if it hasn't exited in time.
pub fn kill(app: &AppHandle) {
    let Some(mut child) = app.state::<EngineProcess>().0.lock().unwrap().take() else {
        return;
    };
    drop(child.stdin.take());
    let deadline = Instant::now() + Duration::from_millis(4000);
    while Instant::now() < deadline {
        match child.try_wait() {
            Ok(Some(_)) => return,
            Ok(None) => std::thread::sleep(Duration::from_millis(50)),
            Err(_) => break,
        }
    }
    let _ = child.kill();
    let _ = child.wait();
}
