#!/usr/bin/env rust-script
//! ```cargo
//! [dependencies]
//! serde_json = "1.0"
//! chrono = "0.4"
//! ```

use serde_json::Value;
use std::env;
use std::io::{self, Read, Write};
use std::fs::File;
use chrono::Local;

fn main() -> io::Result<()> {
    // Read JSON input from Claude Code
    let mut input = String::new();
    io::stdin().read_to_string(&mut input)?;
    
    let data: Value = match serde_json::from_str(&input) {
        Ok(v) => v,
        Err(_) => return Ok(()), // Exit gracefully on invalid JSON
    };
    
    // Get timestamp
    let timestamp = Local::now().format("%H:%M:%S").to_string();
    
    // Check if this is a subagent:stop event
    if let Some(hook_event) = data["hook_event_name"].as_str() {
        if hook_event == "SubagentStop" {
            handle_subagent_stop(&data, &timestamp);
            return Ok(());
        }
    }
    
    // Check both possible field names for tool name (for compatibility)
    let tool_name = data["tool_name"].as_str()
        .or_else(|| data["tool"].as_str())
        .unwrap_or("");
    
    // Get tool input - check both possible field names
    let tool_input = data["tool_input"].as_object()
        .or_else(|| data["args"].as_object());
    
    // Process and display all tool calls
    match tool_name {
        "TodoWrite" => {
            handle_todo_write(&data, &timestamp, tool_input);
        }
        "Read" => {
            if let Some(input) = tool_input {
                if let Some(file_path) = input["file_path"].as_str() {
                    eprintln!("[{}] [READ] Reading file: {}", timestamp, file_path);
                }
            }
        }
        "Write" => {
            if let Some(input) = tool_input {
                if let Some(file_path) = input["file_path"].as_str() {
                    eprintln!("[{}] [WRITE] Writing file: {}", timestamp, file_path);
                }
            }
        }
        "Edit" | "MultiEdit" => {
            if let Some(input) = tool_input {
                if let Some(file_path) = input["file_path"].as_str() {
                    eprintln!("[{}] [EDIT] Editing file: {}", timestamp, file_path);
                }
            }
        }
        "Bash" => {
            if let Some(input) = tool_input {
                if let Some(command) = input["command"].as_str() {
                    eprintln!("[{}] [BASH] Executing: {}", timestamp, command);
                }
            }
        }
        "Grep" => {
            if let Some(input) = tool_input {
                if let Some(pattern) = input["pattern"].as_str() {
                    let path = input["path"].as_str().unwrap_or(".");
                    eprintln!("[{}] [GREP] Searching for '{}' in {}", timestamp, pattern, path);
                }
            }
        }
        "Glob" => {
            if let Some(input) = tool_input {
                if let Some(pattern) = input["pattern"].as_str() {
                    let path = input["path"].as_str().unwrap_or(".");
                    eprintln!("[{}] [GLOB] Finding files matching '{}' in {}", timestamp, pattern, path);
                }
            }
        }
        "LS" => {
            if let Some(input) = tool_input {
                if let Some(path) = input["path"].as_str() {
                    eprintln!("[{}] [LS] Listing directory: {}", timestamp, path);
                }
            }
        }
        "WebFetch" => {
            if let Some(input) = tool_input {
                if let Some(url) = input["url"].as_str() {
                    eprintln!("[{}] [WEB] Fetching: {}", timestamp, url);
                }
            }
        }
        "WebSearch" => {
            if let Some(input) = tool_input {
                if let Some(query) = input["query"].as_str() {
                    eprintln!("[{}] [SEARCH] Searching web for: {}", timestamp, query);
                }
            }
        }
        "Task" => {
            if let Some(input) = tool_input {
                if let Some(description) = input["description"].as_str() {
                    eprintln!("[{}] [TASK] Launching agent: {}", timestamp, description);
                }
            }
        }
        "" => {
            // No tool name, ignore
        }
        _ => {
            // Other tools - show generic message
            eprintln!("[{}] [TOOL] Using: {}", timestamp, tool_name);
        }
    }
    
    Ok(())
}

fn handle_todo_write(data: &Value, timestamp: &str, tool_input: Option<&serde_json::Map<String, Value>>) {
    // Get todos array - check both possible locations
    let todos = tool_input
        .and_then(|input| input["todos"].as_array())
        .or_else(|| data["args"]["todos"].as_array());
    
    if let Some(todos) = todos {
        // Count todo statuses
        let mut pending = 0;
        let mut in_progress = 0;
        let mut completed = 0;
        let mut current_task = None;
        
        for todo in todos {
            match todo["status"].as_str() {
                Some("pending") => pending += 1,
                Some("in_progress") => {
                    in_progress += 1;
                    if current_task.is_none() {
                        current_task = todo["content"].as_str();
                    }
                }
                Some("completed") => completed += 1,
                _ => {}
            }
        }
        
        // Display todo summary
        eprintln!("[{}] [TODO] Updated - Completed: {}, In Progress: {}, Pending: {}", 
                  timestamp, completed, in_progress, pending);
        
        // Display current task if any
        if let Some(task) = current_task {
            eprintln!("[{}] [TODO] Current task: {}", timestamp, task);
            
            // Write to todo file if environment variable is set
            if let Ok(todo_file) = env::var("ALPINE_TODO_FILE") {
                if let Ok(mut file) = File::create(&todo_file) {
                    let _ = file.write_all(task.as_bytes());
                }
            }
        }
    }
}

fn handle_subagent_stop(data: &Value, timestamp: &str) {
    // Extract subagent stop information
    let session_id = data["session_id"].as_str().unwrap_or("unknown");
    let transcript_path = data["transcript_path"].as_str().unwrap_or("unknown");
    let stop_hook_active = data["stop_hook_active"].as_bool().unwrap_or(false);
    
    eprintln!("[{}] [AGENT] Subagent completed - Session: {}", timestamp, session_id);
    
    // Only process transcript if stop_hook_active is false to prevent loops
    if !stop_hook_active && transcript_path != "unknown" {
        // Could process the transcript file here if needed
        eprintln!("[{}] [AGENT] Transcript saved to: {}", timestamp, transcript_path);
    }
}