# Running the Windows package

1. Extract the complete FinstockEventScope-Windows.zip to a folder you control.
2. Open FinstockEventScope/FinstockEventScope.exe. Keep the adjacent _internal folder intact.
3. Start with the visibly labelled synthetic records. No Python installation or terminal command is needed.
4. Read USER_MANUAL.md before enabling an authorized source or configuring notifications.

There is no installer, Windows service or automatic startup registration. User data is created under %LOCALAPPDATA%/Finstock/EventScope. Closing normally minimizes to the tray; use its Quit menu to exit completely. The unsigned build has not undergone a clean-machine deployment pilot. Follow Windows and organizational security policy; do not bypass warnings.

If startup fails, inspect eventscope.log in the data folder and preserve it when reporting the issue. Uninstall by fully quitting and removing the extracted application folder. User history remains in the separate data folder until you intentionally remove it; back it up first if needed.
