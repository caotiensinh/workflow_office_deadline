//! W20B: read-only numeric session probe; no GUI or machine configuration changes.
//! Only a matching nonzero console is a CANDIDATE; never user/IT acceptance.

const UNAVAILABLE: u32 = u32::MAX;

#[derive(Debug, PartialEq, Eq)]
enum Status {
    ServiceSession0,
    NoActiveConsole,
    DifferentConsole,
    CandidateNotUat,
}

fn classify(process: u32, active: Option<u32>) -> Result<Status, &'static str> {
    if process == UNAVAILABLE || active == Some(UNAVAILABLE) {
        return Err("INVALID_SESSION_NUMBER");
    }
    Ok(if process == 0 {
        Status::ServiceSession0
    } else if active.is_none() {
        Status::NoActiveConsole
    } else if active != Some(process) {
        Status::DifferentConsole
    } else {
        Status::CandidateNotUat
    })
}

fn format_result(process: u32, active: Option<u32>) -> Result<String, &'static str> {
    let kind = classify(process, active)?;
    let status = match kind {
        Status::ServiceSession0 => "SESSION_0_GUI_UAT_BLOCKED",
        Status::NoActiveConsole => "NO_ACTIVE_CONSOLE_GUI_UAT_BLOCKED",
        Status::DifferentConsole => "DIFFERENT_SESSION_GUI_UAT_BLOCKED",
        Status::CandidateNotUat => "ACTIVE_CONSOLE_CANDIDATE_NOT_GUI_UAT",
    };
    let console = active
        .map_or_else(|| "null".to_string(), |n| n.to_string());
    let match_console = matches!(kind, Status::CandidateNotUat);
    Ok(format!(
        "{{\"phase\":\"W20B\",\"status\":\"{status}\",\"process_session_id\":{process},\
         \"active_console_session_id\":{console},\"active_console_match\":{match_console},\
         \"live_windows_api_observed\":true,\"human_interaction_observed\":false,\
         \"gui_accepted\":false,\"login_autorun_verified\":false,\
         \"it_approved\":false,\"production_accepted\":false,\"modifies_system\":false}}"
    ))
}

#[cfg(windows)]
mod native {
    #[link(name = "kernel32")]
    extern "system" {
        fn GetCurrentProcessId() -> u32;
        fn ProcessIdToSessionId(process_id: u32, session_id: *mut u32) -> i32;
        fn WTSGetActiveConsoleSessionId() -> u32;
    }

    pub fn inspect_ids() -> Result<(u32, Option<u32>), &'static str> {
        let mut session = u32::MAX;
        // Only read current process ID and numeric session IDs. No handles or mutation.
        let ok = unsafe { ProcessIdToSessionId(GetCurrentProcessId(), &mut session) };
        if ok == 0 {
            return Err("SESSION_QUERY_FAILED");
        }
        let active = unsafe { WTSGetActiveConsoleSessionId() };
        Ok((session, if active == u32::MAX { None } else { Some(active) }))
    }
}

fn run(args: &[String]) -> Result<String, &'static str> {
    if args.len() != 1 {
        return Err("EXPECTED_ONE_MODE");
    }
    match args[0].as_str() {
        "--plan-only" => Ok("{\"phase\":\"W20B\",\"status\":\"PLAN_ONLY_NO_INSPECTION\",\
                           \"live_windows_api_observed\":false,\"human_interaction_observed\":false,\
                           \"gui_accepted\":false,\"it_approved\":false,\
                           \"production_accepted\":false,\"modifies_system\":false}".to_string()),
        "--inspect" => {
            #[cfg(windows)]
            {
                let (process, console) = native::inspect_ids()?;
                format_result(process, console)
            }
            #[cfg(not(windows))]
            {
                Err("WINDOWS_REQUIRED")
            }
        }
        _ => Err("UNRECOGNIZED_MODE"),
    }
}

fn main() {
    let args: Vec<_> = std::env::args().skip(1).collect();
    match run(&args) {
        Ok(result) => println!("{result}"),
        Err(_) => {
            // Prevent leaking local host/session details in failure diagnostics.
            eprintln!("W20B_PROBE_FAILED_CLOSED");
            std::process::exit(2);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test] fn session_zero_blocked() { assert_eq!(classify(0, Some(1)), Ok(Status::ServiceSession0)); }
    #[test] fn session_zero_stays_blocked_when_console_zero() { assert_eq!(classify(0, Some(0)), Ok(Status::ServiceSession0)); }
    #[test] fn console_missing_blocked() { assert_eq!(classify(1, None), Ok(Status::NoActiveConsole)); }
    #[test] fn different_console_blocked() { assert_eq!(classify(3, Some(1)), Ok(Status::DifferentConsole)); }
    #[test] fn any_matching_nonzero_session_candidate() { assert_eq!(classify(2, Some(2)), Ok(Status::CandidateNotUat)); }
    #[test] fn invalid_ids_fail_closed() {
        assert!(classify(UNAVAILABLE, Some(1)).is_err());
        assert!(classify(1, Some(UNAVAILABLE)).is_err());
    }
    #[test] fn structured_evidence_never_approves_production() {
        let output = format_result(1, Some(1)).unwrap();
        assert!(output.contains("\"active_console_match\":true"));
        assert!(output.contains("\"production_accepted\":false"));
        assert!(output.contains("\"gui_accepted\":false"));
        assert!(!output.contains("hostname"));
    }
    #[test] fn plan_mode_does_not_read_win32() {
        let s = run(&["--plan-only".to_string()]).unwrap();
        assert!(s.contains("PLAN_ONLY_NO_INSPECTION"));
        assert!(s.contains("\"live_windows_api_observed\":false"));
    }
    #[test] fn no_args_or_invalid_mode_fails_closed() {
        assert!(run(&[]).is_err());
        assert!(run(&["--inspect".to_string(),"--plan-only".to_string()]).is_err());
        assert!(run(&["--approve".to_string()]).is_err());
    }
}
