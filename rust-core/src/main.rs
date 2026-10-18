//! Deterministic policy engine. No networking, storage, or external crates.
//! Protocol: one CASE per line, tab-separated, with case id encoded as UTF-8 hex.
//! CASE\tHEX_ID\tKIND\tCLASS\tSTATUS\tDAYS\tDUE_STATE\tEXPIRED\tEVIDENCE\tAPPROVAL
//! Output: EVENT\tHEX_ID\tCODE\tSEVERITY
//! Human approvals, external delivery, and sensitive documents are NEVER executed here.
use std::io::{self, BufRead, Write};

#[cfg(test)]
fn utf8_hex(input: &str) -> String {
    input.as_bytes().iter().map(|b| format!("{:02x}", b)).collect()
}
fn decode_hex(input: &str) -> Result<String, String> {
    if input.is_empty() || input.len() % 2 != 0 || input.len() > 1024 {
        return Err("invalid hex length".to_string());
    }
    let mut bytes = Vec::with_capacity(input.len() / 2);
    for chunk in input.as_bytes().chunks_exact(2) {
        let text = std::str::from_utf8(chunk).map_err(|_| "invalid hex ASCII")?;
        bytes.push(u8::from_str_radix(text, 16).map_err(|_| "invalid hex digit")?);
    }
    String::from_utf8(bytes).map_err(|_| "invalid UTF-8".to_string())
}
fn in_set(value: &str, allowed: &[&str]) -> bool { allowed.contains(&value) }
fn evaluate(fields: &[&str]) -> Result<Vec<(&'static str, &'static str)>, String> {
    if fields.len() != 10 || fields[0] != "CASE" { return Err("expected 10 CASE fields".into()); }
    decode_hex(fields[1])?;
    let kind = fields[2]; let class = fields[3]; let status = fields[4];
    if !in_set(kind, &["EMAIL","DOCUMENT","REGULATION","HR","SCHEDULE"]) { return Err("invalid kind".into()); }
    if !in_set(class, &["PUBLIC","INTERNAL","CONFIDENTIAL","RESTRICTED"]) { return Err("invalid class".into()); }
    if !in_set(status, &["NEW","TRIAGE","DRAFT","IN_PROGRESS","READY_FOR_APPROVAL","APPROVED","COMPLETED","REJECTED","CANCELLED"]) { return Err("invalid status".into()); }
    let days: i64 = fields[5].parse().map_err(|_| "invalid days")?;
    if days < -365_000 || days > 365_000 { return Err("days out of range".into()); }
    let due_state = fields[6];
    if !in_set(due_state, &["NONE", "UNVERIFIED", "VERIFIED"]) { return Err("invalid due_state".into()); }
    if !in_set(fields[7], &["0", "1"]) || !in_set(fields[8], &["0", "1"]) { return Err("invalid boolean".into()); }
    let expired = fields[7] == "1";
    let evidence = fields[8] == "1";
    let approval = fields[9];
    if !in_set(approval, &["NOT_REQUIRED","PENDING","APPROVED","REJECTED"]) { return Err("invalid approval".into()); }
    if in_set(status, &["COMPLETED","REJECTED","CANCELLED"]) { return Ok(vec![]); }
    let mut out = vec![];
    if due_state != "VERIFIED" {
        out.push(("VERIFY_DEADLINE", "WARNING"));
    } else if days == 3 {
        out.push(("D_MINUS_3", "INFO"));
    } else if days == 1 {
        out.push(("D_MINUS_1", "WARNING"));
    } else if days == 0 {
        out.push((if expired { "OVERDUE_TODAY" } else { "DUE_TODAY" }, "WARNING"));
    } else if days < 0 {
        out.push(("OVERDUE", "CRITICAL"));
    }
    let missing_evidence = in_set(kind, &["HR", "REGULATION", "DOCUMENT"]) && !evidence;
    if missing_evidence {
        out.push(("MISSING_EVIDENCE", "CRITICAL"));
    } else if status == "READY_FOR_APPROVAL" && approval != "APPROVED" {
        if approval == "REJECTED" { out.push(("REJECTED_REVIEW", "WARNING")); }
        else { out.push(("APPROVAL_PENDING", "WARNING")); }
    }
    Ok(out)
}
fn run(input: impl BufRead, mut output: impl Write) -> Result<(), String> {
    for (index, line) in input.lines().enumerate() {
        let line = line.map_err(|e| format!("read error: {e}"))?;
        if line.trim().is_empty() { continue; }
        let fields: Vec<&str> = line.split('\t').collect();
        let events = evaluate(&fields).map_err(|e| format!("line {}: {}", index+1, e))?;
        for (code, severity) in events {
            writeln!(output, "EVENT\t{}\t{}\t{}", fields[1], code, severity).map_err(|e| format!("write error: {e}"))?;
        }
    }
    Ok(())
}
fn main() {
    if let Err(e) = run(io::stdin().lock(), io::stdout().lock()) {
        eprintln!("POLICY_INPUT_ERROR: {e}");
        std::process::exit(2);
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    fn fields(status: &'static str, days: &'static str, due: &'static str, evidence: &'static str) -> Vec<&'static str> {
        vec!["CASE", "4544552d303031", "DOCUMENT", "INTERNAL", status, days, due, "0", evidence, "PENDING"]
    }
    #[test] fn d3() { assert_eq!(evaluate(&fields("IN_PROGRESS", "3", "VERIFIED", "1")).unwrap(), vec![("D_MINUS_3", "INFO")]); }
    #[test] fn overdue() { assert!(evaluate(&fields("IN_PROGRESS", "-2", "VERIFIED", "1")).unwrap().iter().any(|x| x.0 == "OVERDUE")); }
    #[test] fn completed_silent() { assert!(evaluate(&fields("COMPLETED", "-2", "VERIFIED", "1")).unwrap().is_empty()); }
    #[test] fn evidence_blocks_request() { let out=evaluate(&fields("READY_FOR_APPROVAL", "1", "VERIFIED", "0")).unwrap(); assert!(out.iter().any(|x| x.0 == "MISSING_EVIDENCE")); assert!(!out.iter().any(|x| x.0 == "APPROVAL_PENDING")); }
    #[test] fn reject_bad_input() { let mut f=fields("IN_PROGRESS", "3", "VERIFIED", "1"); f[5]="tomorrow"; assert!(evaluate(&f).is_err()); }
    #[test] fn hex_roundtrip() { assert_eq!(decode_hex(&utf8_hex("教育-001")).unwrap(), "教育-001"); }
    #[test] fn output() { let input = b"CASE\t4544552d303031\tEMAIL\tINTERNAL\tIN_PROGRESS\t3\tVERIFIED\t0\t1\tNOT_REQUIRED\n"; let mut output = vec![]; run(&input[..], &mut output).unwrap(); assert_eq!(String::from_utf8(output).unwrap(), "EVENT\t4544552d303031\tD_MINUS_3\tINFO\n"); }
}
