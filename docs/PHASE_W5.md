# Phase W5 — Desktop visibility, one-click Windows package and opt-in login startup

## Goal and safety boundary
Provide a portable Windows notification-center EXE and explicitly user-opted-in current-user Startup shortcut, with no administrator privileges, global registry writes, new service, scheduled tasks or access to the institution's email. **The existing MRCAO self-hosted runner is Session 0, so actual visible GUI acceptance is still blocked without a signed-in interactive Windows account.**

## W5 code
- \`desktop_app.launch\` refuses to start a fake desktop UI in Windows Session 0; the exception names the limitation.
- Notification bells now re-trigger **once** when a snoozed alert disappears and later reappears, while ordinary refreshes do not spam.
- \`windows/build_desktop.ps1\` packages \`windows/notification_entry.py\` to \`dist/EDUNotifications.exe\` with PyInstaller on a Windows CI runner. Python and Tkinter are bundled into an unsigned EXE; check antivirus/SmartScreen and organizational policy before deployment.
- \`windows/manage_desktop_startup.ps1\` defaults to **PlanOnly**, returning a JSON description with no mutation.
- The opt-in \`-Install\` action creates a **current-user Startup-folder link**, not an elevated task or service. It refuses production installation from Session 0.
- \`-Remove\` rolls back only the shortcut owned by this project; unknown/conflicting links are not modified.
- A CI-only isolated Startup directory inside GitHub \`RUNNER_TEMP\` proves install/no-overwrite/remove without touching the real user's Startup.

## Operator workflow after institutional review
1. Obtain and independently hash-check the W5 Windows EXE from the successful GitHub Actions artifact. The executable is **unsigned** and not a production release.
2. Run a synthetic sample in a writable user-owned folder, not a shared school database; ensure the EXE and DB are allowed under institutional IT policy.
3. Run \`windows/manage_desktop_startup.ps1 -PlanOnly -Executable <approved-exe-path> -DbPath <user-owned-db-path>\`.
4. From a real **signed-in interactive user account** (not MRCAO Session 0), after IT approval, \`-Install\` can register login startup. Do not allow a service runner to configure the user's Startup.
5. Roll back with the matching \`-Remove\` options; it removes only this project's shortcut and does not alter the background Python/Rust worker.

## CI and field acceptance
- [ ] W5 new Tk callback/regression suite and W4 model PASS.
- [ ] One-file Windows desktop EXE built and \`--help\` smoke tested.
- [ ] Startup test in **isolated** directory succeeds; no real user Startup changes.
- [ ] On MRCAO, Session ID captured, UI availability truthfully reported.
- [ ] W5 PR merged, main CI PASS.
- [ ] Real desktop visible UI screenshot *of only our app*, bell, keyboard/mouse button clicks, after-login startup, logoff safety confirmed in interactive user session (external blocker).
- [ ] Approved production Outlook, SMTP, SSO and IT data-protection acceptance (external blocker).

## Why real GUI acceptance is still separate
GitHub Actions service-based Windows runners execute in Session 0 and cannot display a Tkinter window in another user's desktop session by design. Running a process from Session 0 cannot prove users saw an alert. Never launch in someone else's login session, inject clicks, read the real desktop, or alter account startup without explicit local consent. This project therefore reports **CI package and model PASS** separately from **interactive visual acceptance pending**.
