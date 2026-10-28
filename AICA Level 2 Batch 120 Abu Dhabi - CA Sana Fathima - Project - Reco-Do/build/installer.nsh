; Reco-Do installer customisation (included by electron-builder; see electron-builder.yml, nsis.include).
;
; People sometimes keep the installer and double-click it again instead of the Reco-Do shortcut. When the same
; or a newer version is already installed, say so plainly and offer to open the installed app instead of
; reinstalling. Silent installs (/S) and the elevated second instance of the installer are never interrupted.

!include "WordFunc.nsh"

!macro customInit
  ${IfNot} ${Silent}
  ${AndIfNot} ${UAC_IsInnerInstance}
    ; electron-builder records the installed version under the uninstall key (DisplayVersion) and the folder
    ; under its own key (InstallLocation): HKCU for a per-user install (the default), HKLM for all users.
    StrCpy $R8 ""
    StrCpy $R9 ""
    ReadRegStr $R8 HKCU "${UNINSTALL_REGISTRY_KEY}" "DisplayVersion"
    ReadRegStr $R9 HKCU "${INSTALL_REGISTRY_KEY}" "InstallLocation"
    ${If} $R8 == ""
      ReadRegStr $R8 HKLM "${UNINSTALL_REGISTRY_KEY}" "DisplayVersion"
      ReadRegStr $R9 HKLM "${INSTALL_REGISTRY_KEY}" "InstallLocation"
    ${EndIf}

    ; The installed program: RecoDo.exe from 1.1.2 on, Reco-Do.exe in older versions.
    StrCpy $R6 ""
    ${If} $R9 != ""
      ${If} ${FileExists} "$R9\${APP_EXECUTABLE_FILENAME}"
        StrCpy $R6 "$R9\${APP_EXECUTABLE_FILENAME}"
      ${ElseIf} ${FileExists} "$R9\Reco-Do.exe"
        StrCpy $R6 "$R9\Reco-Do.exe"
      ${EndIf}
    ${EndIf}

    ; Only when the app is really there: a left-over registry entry without the app means "not installed".
    ${If} $R8 != ""
    ${AndIf} $R6 != ""
      ; 0 = same version, 1 = the installed one is newer, 2 = this installer is newer (an update: no question).
      ${VersionCompare} "$R8" "${VERSION}" $R7
      ${If} $R7 != 2
        MessageBox MB_YESNO|MB_ICONQUESTION|MB_DEFBUTTON2|MB_TOPMOST|MB_SETFOREGROUND \
          "${PRODUCT_NAME} $R8 is already installed.$\r$\n$\r$\nTo open it, use the ${PRODUCT_NAME} shortcut on your Desktop or Start menu.$\r$\n$\r$\nClick Yes to reinstall/repair, No to open ${PRODUCT_NAME} now." \
          /SD IDYES IDYES reco_do_reinstall
        Exec '"$R6"'
        Quit
        reco_do_reinstall:
      ${EndIf}
    ${EndIf}
  ${EndIf}
!macroend
