use rdev::{listen, Event, EventType};
use serde::Serialize;
use serde_json::json;
use std::thread;
use std::time::Duration;

#[derive(Serialize)]
struct RdevEvent {
    event_type: String,
    name: Option<String>,
    time: std::time::SystemTime,
    data: String,
}

fn deal_event_to_json(event: Event) -> RdevEvent {
    let mut jsonify_event = RdevEvent {
        event_type: "".to_string(),
        name: event.name,
        time: event.time,
        data: "".to_string(),
    };
    match event.event_type {
        EventType::KeyPress(key) => {
            jsonify_event.event_type = "KeyPress".to_string();
            jsonify_event.data = json!({
                "key": format!("{:?}", key)
            })
            .to_string();
        }
        EventType::KeyRelease(key) => {
            jsonify_event.event_type = "KeyRelease".to_string();
            jsonify_event.data = json!({
                "key": format!("{:?}", key)
            })
            .to_string();
        }
        _ => {}
    }
    jsonify_event
}

fn write_text_slow(text: &str) {
    use enigo::{Enigo, Keyboard, Settings};
    let mut enigo = Enigo::new(&Settings::default()).unwrap();
    enigo.text(text).unwrap();
}

fn write_text_fast(text: &str) {
    use clipboard_win::{formats, get_clipboard_string, set_clipboard};
    use enigo::{Direction, Enigo, Key, Keyboard, Settings};

    // Retry logic for clipboard (helps when app is in background/minimized)
    let old_clipboard = get_clipboard_string().unwrap_or_default();
    let mut clipboard_set = false;

    // Try up to 3 times to set clipboard
    for _ in 0..3 {
        if let Ok(_) = set_clipboard(formats::Unicode, text) {
            clipboard_set = true;
            break;
        }
        thread::sleep(Duration::from_millis(50));
    }

    if !clipboard_set {
        eprintln!("Failed to set clipboard after retries. Fallback to slow write.");
        write_text_slow(text);
        return;
    }

    // Small delay to ensure clipboard is ready
    thread::sleep(Duration::from_millis(50));

    // Simulate Ctrl+V (paste)
    let mut enigo = Enigo::new(&Settings::default()).unwrap();

    // Press Ctrl
    if let Err(e) = enigo.key(Key::Control, Direction::Press) {
        eprintln!("Failed to press Ctrl: {:?}", e);
        write_text_slow(text); // Fallback
        return;
    }

    // Press V
    if let Err(e) = enigo.key(Key::Unicode('v'), Direction::Click) {
        eprintln!("Failed to press V: {:?}", e);
    }

    // Release Ctrl
    if let Err(e) = enigo.key(Key::Control, Direction::Release) {
        eprintln!("Failed to release Ctrl: {:?}", e);
    }

    // Wait for paste to complete
    thread::sleep(Duration::from_millis(100));

    // Restore original clipboard
    if !old_clipboard.is_empty() {
        // Try to restore, but don't panic if it fails
        let _ = set_clipboard(formats::Unicode, &old_clipboard);
    }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();

    if args.len() > 1 && args[1] == "listen" {
        if let Err(error) = listen(move |event| match event.event_type {
            EventType::KeyPress(_) | EventType::KeyRelease(_) => {
                let event = deal_event_to_json(event);
                println!("{}", serde_json::to_string(&event).unwrap());
            }
            _ => {}
        }) {
            println!("!error: {:?}", error);
        }
    }

    if args.len() > 2 && args[1] == "write" {
        let text = args[2].clone();
        write_text_fast(text.as_str());
    }

    if args.len() > 2 && args[1] == "write-slow" {
        let text = args[2].clone();
        write_text_slow(text.as_str());
    }

    if args.len() > 1 && args[1] == "toggle-caps" {
        use enigo::{Direction, Enigo, Key, Keyboard, Settings};
        let mut enigo = Enigo::new(&Settings::default()).unwrap();
        let _ = enigo.key(Key::CapsLock, Direction::Click);
    }

    if args.len() > 1 && args[1] == "press-enter" {
        use enigo::{Direction, Enigo, Key, Keyboard, Settings};
        let mut enigo = Enigo::new(&Settings::default()).unwrap();
        let _ = enigo.key(Key::Return, Direction::Click);
    }
}
