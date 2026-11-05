// VKL Outlook Helper - opens a draft e-mail in CLASSIC Outlook (desktop) with
// the Excel file attached. Started by Windows when the tool's Email button
// opens a vklmail:// link. Standard library only. No network except the
// office LAN server named in the link.
package main

import (
	"fmt"
	"io"
	"net"
	"net/http"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"runtime"
	"strings"
	"time"
)

const helperVersion = "1.1.0"

var idRe = regexp.MustCompile(`^[0-9a-f]{32}$`)

func psExe() string {
	if v := os.Getenv("VKL_PS"); v != "" {
		return v
	}
	return "powershell.exe"
}

func hidden(c *exec.Cmd) { hideWindow(c) }

func msgBox(title, text string) {
	if os.Getenv("VKL_PS") != "" {
		fmt.Fprintln(os.Stderr, title+": "+text)
		return
	}
	script := `Add-Type -AssemblyName PresentationFramework; [void][System.Windows.MessageBox]::Show($env:VKL_MSG,$env:VKL_TITLE)`
	c := exec.Command(psExe(), "-NoProfile", "-NonInteractive", "-Command", script)
	c.Env = append(os.Environ(), "VKL_MSG="+text, "VKL_TITLE="+title)
	hidden(c)
	_ = c.Run()
}

func privateHost(h string) bool {
	host, _, err := net.SplitHostPort(h)
	if err != nil {
		host = h
	}
	if host == "localhost" {
		return true
	}
	ip := net.ParseIP(host)
	if ip == nil {
		return !strings.Contains(host, ".") && host != ""
	}
	return ip.IsLoopback() || ip.IsPrivate()
}

func sanitize(s string) string {
	var b strings.Builder
	for _, r := range s {
		if r < 32 || strings.ContainsRune(`\/:*?"<>|`, r) {
			continue
		}
		b.WriteRune(r)
	}
	out := strings.TrimSpace(b.String())
	if out == "" {
		out = "VKL_Report.xlsx"
	}
	return out
}

const draftScript = `$ErrorActionPreference='Stop'
try { $ol=[Runtime.InteropServices.Marshal]::GetActiveObject('Outlook.Application') } catch { $ol=New-Object -ComObject Outlook.Application }
$m=$ol.CreateItem(0)
$m.Subject=$env:VKL_SUBJECT
[void]$m.Attachments.Add($env:VKL_FILE)
$m.Display()
`

func makeDraft(link string) error {
	u, err := url.Parse(link)
	if err != nil || u.Scheme != "vklmail" {
		return fmt.Errorf("unexpected link")
	}
	q := u.Query()
	host, id, subject := q.Get("host"), q.Get("id"), q.Get("subject")
	if !privateHost(host) || !idRe.MatchString(id) {
		return fmt.Errorf("the link does not point to your office server")
	}
	cl := &http.Client{Timeout: 30 * time.Second}
	resp, err := cl.Get("http://" + host + "/api/outbox/" + id)
	if err != nil {
		return fmt.Errorf("cannot reach the VKL server %s: %v", host, err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		return fmt.Errorf("the file has expired - click the Email button again")
	}
	data, err := io.ReadAll(io.LimitReader(resp.Body, 12<<20))
	if err != nil || len(data) < 4 {
		return fmt.Errorf("the file could not be read")
	}
	name := sanitize(resp.Header.Get("X-Filename"))
	dir := filepath.Join(os.TempDir(), "VKL_Outlook", fmt.Sprint(time.Now().UnixNano()))
	if err := os.MkdirAll(dir, 0o700); err != nil {
		return err
	}
	file := filepath.Join(dir, name)
	if err := os.WriteFile(file, data, 0o600); err != nil {
		return err
	}
	cleanOld(filepath.Join(os.TempDir(), "VKL_Outlook"))
	c := exec.Command(psExe(), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", draftScript)
	c.Env = append(os.Environ(), "VKL_SUBJECT="+subject, "VKL_FILE="+file)
	hidden(c)
	out, err := c.CombinedOutput()
	if err != nil {
		return fmt.Errorf("Outlook could not create the draft. Classic Outlook (desktop) must be installed: %s", strings.TrimSpace(string(out)))
	}
	return nil
}

func cleanOld(root string) {
	ents, _ := os.ReadDir(root)
	for _, e := range ents {
		if fi, err := e.Info(); err == nil && time.Since(fi.ModTime()) > 24*time.Hour {
			_ = os.RemoveAll(filepath.Join(root, e.Name()))
		}
	}
}

func regAdd(args ...string) error {
	c := exec.Command("reg", append([]string{"add"}, args...)...)
	hidden(c)
	return c.Run()
}

func install() error {
	self, err := os.Executable()
	if err != nil {
		return err
	}
	dir := filepath.Join(os.Getenv("LOCALAPPDATA"), "VKL_Outlook_Helper")
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return err
	}
	dst := filepath.Join(dir, "VKL_Outlook_Helper.exe")
	if !strings.EqualFold(self, dst) {
		b, err := os.ReadFile(self)
		if err != nil {
			return err
		}
		if err := os.WriteFile(dst, b, 0o755); err != nil {
			return err
		}
	}
	key := `HKCU\Software\Classes\vklmail`
	if err := regAdd(key, "/ve", "/d", "URL:VKL Outlook Draft", "/f"); err != nil {
		return err
	}
	if err := regAdd(key, "/v", "URL Protocol", "/d", "", "/f"); err != nil {
		return err
	}
	return regAdd(key+`\shell\open\command`, "/ve", "/d", `"`+dst+`" "%1"`, "/f")
}

func uninstall() {
	c := exec.Command("reg", "delete", `HKCU\Software\Classes\vklmail`, "/f")
	hidden(c)
	_ = c.Run()
}

func main() {
	if len(os.Args) < 2 {
		msgBox("VKL Outlook Helper", "Run install.bat once to set this up. Version "+helperVersion)
		return
	}
	switch os.Args[1] {
	case "--install":
		if runtime.GOOS != "windows" {
			fmt.Println("windows only")
			return
		}
		if err := install(); err != nil {
			msgBox("VKL Outlook Helper", "Install failed: "+err.Error())
			os.Exit(1)
		}
		msgBox("VKL Outlook Helper", "Installed. The Email buttons in the converter now open a classic Outlook draft with the Excel attached.\n\nThe first time, Chrome or Edge asks to open this app: tick 'Always allow' and click Open.")
	case "--uninstall":
		uninstall()
		msgBox("VKL Outlook Helper", "Removed.")
	default:
		if err := makeDraft(os.Args[1]); err != nil {
			msgBox("VKL Outlook Helper", err.Error())
			os.Exit(1)
		}
	}
}
