package main

import (
	"context"
	_ "embed"
	"encoding/csv"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"sync"
	"syscall"
	"time"
)

// Embedded web assets
//
//go:embed web/index.html
var rawIndexHTML []byte

//go:embed web/shim.js
var rawShimJS []byte

const (
	AppVersion     = "1.1.0"
	MaxBodyBytes   = 5 * 1024 * 1024 // 5 MB max
	MaxListCount   = 20000
	MaxLogFileSize = 5 * 1024 * 1024 // 5 MB rotation
	MaxLogFiles    = 5
	MaxHistoryKeep = 20
)

// Config representation
type Config struct {
	Port    int    `json:"port"`
	Pin     string `json:"pin"`
	DataDir string `json:"dataDir"`
}

// Master SKU Item structure: { u, s, n, c }
type SkuItem struct {
	U string `json:"u"` // Unit
	S string `json:"s"` // Customer SKU
	N string `json:"n"` // Description / Name
	C string `json:"c"` // ERP SKU Code (required non-empty)
}

// Master document structure: { name, at, list }
type MasterDocument struct {
	Name string    `json:"name"`
	At   string    `json:"at"`
	List []SkuItem `json:"list"`
}

// Server state
type ServerApp struct {
	mu           sync.RWMutex
	cfg          Config
	startTime    time.Time
	hostname     string
	injectedHTML []byte
	currentDoc   *MasterDocument
	rawDocBytes  []byte
	logFile      *os.File
	logSize      int64
	logMu        sync.Mutex
}

func main() {
	app := &ServerApp{
		startTime: time.Now(),
		cfg: Config{
			Port:    8080,
			Pin:     "",
			DataDir: "data",
		},
	}

	// 0. Always work from the folder that holds the program. A Windows scheduled task starts in
	//    C:\Windows\System32, which would otherwise make config.json, data and logs land there.
	if exe, err := os.Executable(); err == nil {
		_ = os.Chdir(filepath.Dir(exe))
	}

	// 1. Hostname
	host, err := os.Hostname()
	if err != nil {
		host = "WINDOWS-SERVER"
	}
	app.hostname = host

	// 2. Load or create config.json
	app.loadOrCreateConfig()

	// 3. Ensure directories exist
	if err := os.MkdirAll(app.cfg.DataDir, 0755); err != nil {
		fmt.Printf("Error creating data directory: %v\n", err)
	}
	historyDir := filepath.Join(app.cfg.DataDir, "history")
	if err := os.MkdirAll(historyDir, 0755); err != nil {
		fmt.Printf("Error creating history directory: %v\n", err)
	}
	if err := os.MkdirAll("logs", 0755); err != nil {
		fmt.Printf("Error creating logs directory: %v\n", err)
	}

	// 4. Initialize rotating log file
	app.initLogging()

	// 5. Load existing master if present
	app.loadExistingMaster()

	// 6. Prepare injected index.html with shim.js
	app.prepareInjectedHTML()

	// 7. Discover LAN IPv4 addresses
	lanURLs := app.getLanURLs(app.cfg.Port)

	// Print startup banner
	app.printStartupBanner(lanURLs)

	// 8. Configure HTTP Router (Universal Go standard library compatibility)
	mux := http.NewServeMux()
	mux.HandleFunc("/", app.handleRoot)
	mux.HandleFunc("/api/health", app.handleHealth)
	mux.HandleFunc("/api/master", app.handleMaster)
	mux.HandleFunc("/api/outbox", app.handleOutbox)
	mux.HandleFunc("/api/outbox/", app.handleOutbox)
	mux.HandleFunc("/admin", app.handleAdmin)
	mux.HandleFunc("/admin/restore", app.handleAdminRestore)
	mux.HandleFunc("/admin/download", app.handleAdminDownload)

	listenAddr := fmt.Sprintf("0.0.0.0:%d", app.cfg.Port)
	server := &http.Server{
		Addr:         listenAddr,
		Handler:      app.securityHeadersMiddleware(mux),
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 20 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	// Listen
	ln, err := net.Listen("tcp", listenAddr)
	if err != nil {
		app.logMsg(fmt.Sprintf("FATAL: Port %d is already in use by another program: %v", app.cfg.Port, err))
		fmt.Printf("\n[ERROR] Port %d is already in use by another application.\n", app.cfg.Port)
		fmt.Printf("Please close the conflicting program or change \"port\" in config.json.\n\n")
		os.Exit(1)
	}

	// Handle graceful shutdown on Ctrl+C / SIGTERM
	stopChan := make(chan os.Signal, 1)
	signal.Notify(stopChan, os.Interrupt, syscall.SIGTERM)

	go func() {
		<-stopChan
		fmt.Println("\nReceived shutdown signal. Stopping VKL Order Converter server gracefully...")
		app.logMsg("Server shutting down gracefully.")
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		_ = server.Shutdown(ctx)
		if app.logFile != nil {
			_ = app.logFile.Close()
		}
		os.Exit(0)
	}()

	app.logMsg(fmt.Sprintf("Server started on %s (Port %d)", app.hostname, app.cfg.Port))
	if err := server.Serve(ln); err != nil && !errors.Is(err, http.ErrServerClosed) {
		app.logMsg(fmt.Sprintf("Server exited with error: %v", err))
		log.Fatalf("Server error: %v", err)
	}
}

// Prepare injected HTML by injecting shim.js directly after <head>
func (app *ServerApp) prepareInjectedHTML() {
	htmlStr := string(rawIndexHTML)
	shimSnippet := "\n  <!-- VKL LAN Sync Shim (Injected at Serve Time) -->\n  <script>\n" + string(rawShimJS) + "\n  </script>\n"

	headIdx := strings.Index(strings.ToLower(htmlStr), "<head>")
	if headIdx != -1 {
		insertPoint := headIdx + len("<head>")
		app.injectedHTML = []byte(htmlStr[:insertPoint] + shimSnippet + htmlStr[insertPoint:])
	} else {
		// Fallback if <head ...> has attributes
		headIdx = strings.Index(strings.ToLower(htmlStr), "<head")
		if headIdx != -1 {
			closingBracket := strings.Index(htmlStr[headIdx:], ">")
			if closingBracket != -1 {
				insertPoint := headIdx + closingBracket + 1
				app.injectedHTML = []byte(htmlStr[:insertPoint] + shimSnippet + htmlStr[insertPoint:])
			} else {
				app.injectedHTML = append([]byte(shimSnippet), rawIndexHTML...)
			}
		} else {
			app.injectedHTML = append([]byte(shimSnippet), rawIndexHTML...)
		}
	}
}

// Config loading and saving
func (app *ServerApp) loadOrCreateConfig() {
	configPath := "config.json"
	data, err := os.ReadFile(configPath)
	if err == nil {
		var c Config
		if err := json.Unmarshal(data, &c); err == nil {
			if c.Port > 0 {
				app.cfg.Port = c.Port
			}
			app.cfg.Pin = c.Pin
			if c.DataDir != "" {
				app.cfg.DataDir = c.DataDir
			}
			return
		}
	}

	// Create default config
	app.cfg = Config{
		Port:    8080,
		Pin:     "",
		DataDir: "data",
	}
	out, _ := json.MarshalIndent(app.cfg, "", "  ")
	_ = os.WriteFile(configPath, out, 0644)
}

// Load existing master if found in data/master.json
func (app *ServerApp) loadExistingMaster() {
	masterPath := filepath.Join(app.cfg.DataDir, "master.json")
	data, err := os.ReadFile(masterPath)
	if err == nil && len(data) > 0 {
		var doc MasterDocument
		if err := json.Unmarshal(data, &doc); err == nil && len(doc.List) > 0 {
			app.currentDoc = &doc
			app.rawDocBytes = data
			app.logMsg(fmt.Sprintf("Loaded existing master: %s (%d SKUs)", doc.Name, len(doc.List)))
		}
	}
}

// Discover all LAN IPv4 addresses
func (app *ServerApp) getLanURLs(port int) []string {
	var urls []string
	interfaces, err := net.Interfaces()
	if err != nil {
		return []string{fmt.Sprintf("http://127.0.0.1:%d", port)}
	}

	for _, iface := range interfaces {
		if iface.Flags&net.FlagUp == 0 || iface.Flags&net.FlagLoopback != 0 {
			continue
		}
		addrs, err := iface.Addrs()
		if err != nil {
			continue
		}
		for _, addr := range addrs {
			ipNet, ok := addr.(*net.IPNet)
			if ok && !ipNet.IP.IsLoopback() && ipNet.IP.To4() != nil {
				ip4 := ipNet.IP.To4().String()
				urls = append(urls, fmt.Sprintf("http://%s:%d", ip4, port))
			}
		}
	}

	if len(urls) == 0 {
		urls = append(urls, fmt.Sprintf("http://127.0.0.1:%d", port))
	}
	return urls
}

func (app *ServerApp) printStartupBanner(lanURLs []string) {
	fmt.Println("==================================================================")
	fmt.Println("  VKL CUSTOMER ORDER TO ERP CONVERTER - LAN SERVER (v1.0.0)")
	fmt.Println("==================================================================")
	fmt.Printf("  Machine Hostname : %s\n", app.hostname)
	fmt.Printf("  Listen Port      : %d\n", app.cfg.Port)
	if app.cfg.Pin != "" {
		fmt.Printf("  PIN Protection   : ENABLED (Required for master uploads)\n")
	} else {
		fmt.Printf("  PIN Protection   : DISABLED (Open office collaboration)\n")
	}
	fmt.Printf("  Data Directory   : %s\n", app.cfg.DataDir)
	fmt.Printf("  Log File         : logs/server.log\n")
	fmt.Println("------------------------------------------------------------------")
	fmt.Println("  SHARE THESE URLS WITH YOUR OFFICE COLLEAGUES (Chrome / Edge):")
	for _, u := range lanURLs {
		fmt.Printf("   -> %s\n", u)
	}
	fmt.Printf("   -> Admin Dashboard: http://localhost:%d/admin\n", app.cfg.Port)
	fmt.Println("==================================================================")
	fmt.Println("  Press Ctrl+C to stop the server gracefully.")
	fmt.Println()
}

// Middleware: Standard security headers
func (app *ServerApp) securityHeadersMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("X-Content-Type-Options", "nosniff")
		w.Header().Set("Referrer-Policy", "no-referrer")
		w.Header().Set("X-Frame-Options", "SAMEORIGIN")
		next.ServeHTTP(w, r)
	})
}

// GET / - Serve injected HTML with Cache-Control: no-cache
func (app *ServerApp) handleRoot(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path != "/" {
		http.NotFound(w, r)
		return
	}
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.Header().Set("Cache-Control", "no-cache, no-store, must-revalidate")
	w.WriteHeader(http.StatusOK)

	// Put the current shared master into the page so every user starts with the same ERP master.
	masterJSON := "null"
	app.mu.RLock()
	if app.currentDoc != nil && len(app.rawDocBytes) > 0 {
		masterJSON = strings.ReplaceAll(string(app.rawDocBytes), "<", "\\u003c")
	}
	app.mu.RUnlock()
	page := strings.Replace(string(app.injectedHTML), "/*__VKL_SHARED_MASTER__*/null", masterJSON, 1)
	_, _ = w.Write([]byte(page))
}

// GET /api/health
func (app *ServerApp) handleHealth(w http.ResponseWriter, r *http.Request) {
	app.mu.RLock()
	defer app.mu.RUnlock()

	var skus int
	var updated string
	if app.currentDoc != nil {
		skus = len(app.currentDoc.List)
		updated = app.currentDoc.At
	}

	resp := map[string]interface{}{
		"ok":            true,
		"version":       AppVersion,
		"host":          app.hostname,
		"masterSkus":    skus,
		"masterUpdated": updated,
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	_ = json.NewEncoder(w).Encode(resp)
}

// /api/master dispatcher
func (app *ServerApp) handleMaster(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		app.handleGetMaster(w, r)
	case http.MethodPut:
		app.handlePutMaster(w, r)
	default:
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
	}
}

// GET /api/master
func (app *ServerApp) handleGetMaster(w http.ResponseWriter, r *http.Request) {
	app.mu.RLock()
	defer app.mu.RUnlock()

	if app.currentDoc == nil || len(app.rawDocBytes) == 0 {
		w.WriteHeader(http.StatusNoContent)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write(app.rawDocBytes)
}

// PUT /api/master
func (app *ServerApp) handlePutMaster(w http.ResponseWriter, r *http.Request) {
	clientIP := getClientIP(r)

	// PIN Verification
	if app.cfg.Pin != "" {
		reqPin := strings.TrimSpace(r.Header.Get("X-VKL-Pin"))
		if reqPin != app.cfg.Pin {
			app.appendAudit(clientIP, "PUT_MASTER_AUTH_FAILED", 0, "")
			http.Error(w, `{"error":"Invalid or missing PIN"}`, http.StatusUnauthorized)
			return
		}
	}

	// 5 MB limit
	r.Body = http.MaxBytesReader(w, r.Body, MaxBodyBytes)
	bodyBytes, err := io.ReadAll(r.Body)
	if err != nil {
		http.Error(w, `{"error":"Payload too large or read error (Max 5MB)"}`, http.StatusBadRequest)
		return
	}

	// Validate JSON schema
	var doc MasterDocument
	if err := json.Unmarshal(bodyBytes, &doc); err != nil {
		http.Error(w, `{"error":"Invalid JSON: `+err.Error()+`"}`, http.StatusBadRequest)
		return
	}

	if len(doc.List) == 0 || len(doc.List) > MaxListCount {
		http.Error(w, fmt.Sprintf(`{"error":"list must contain between 1 and %d items"}`, MaxListCount), http.StatusBadRequest)
		return
	}

	// Validate each item: u,s,n,c strings and non-empty c
	for i, item := range doc.List {
		if strings.TrimSpace(item.C) == "" {
			http.Error(w, fmt.Sprintf(`{"error":"Item at index %d has empty ERP code 'c'"}`, i), http.StatusBadRequest)
			return
		}
	}

	if doc.At == "" {
		doc.At = time.Now().UTC().Format(time.RFC3339)
	}
	if doc.Name == "" {
		doc.Name = fmt.Sprintf("Master_%s.json", time.Now().Format("20060102_150405"))
	}

	cleanBytes, err := json.Marshal(doc)
	if err != nil {
		http.Error(w, `{"error":"Serialization error"}`, http.StatusInternalServerError)
		return
	}

	// Lock mutex for atomic write
	app.mu.Lock()
	defer app.mu.Unlock()

	masterPath := filepath.Join(app.cfg.DataDir, "master.json")
	if err := atomicWriteFile(masterPath, cleanBytes); err != nil {
		app.logMsg(fmt.Sprintf("Failed to write master.json: %v", err))
		http.Error(w, `{"error":"Failed to persist master file"}`, http.StatusInternalServerError)
		return
	}

	// Save history file: master_YYYYMMDD_HHMMSS.json
	histFileName := fmt.Sprintf("master_%s.json", time.Now().Format("20060102_150405"))
	histPath := filepath.Join(app.cfg.DataDir, "history", histFileName)
	_ = os.WriteFile(histPath, cleanBytes, 0644)

	// Clean older history, keep last 20
	app.cleanHistory()

	// Update memory state
	app.currentDoc = &doc
	app.rawDocBytes = cleanBytes

	// Log audit
	app.appendAudit(clientIP, "UPLOAD_MASTER", len(doc.List), doc.Name)
	app.logMsg(fmt.Sprintf("Master updated by %s: %s (%d SKUs)", clientIP, doc.Name, len(doc.List)))

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	_ = json.NewEncoder(w).Encode(map[string]interface{}{
		"ok":      true,
		"message": "Master updated successfully",
		"skus":    len(doc.List),
		"at":      doc.At,
		"name":    doc.Name,
	})
}

// Atomic file write using temporary file in same directory and atomic rename
func atomicWriteFile(destPath string, data []byte) error {
	dir := filepath.Dir(destPath)
	tmpFile, err := os.CreateTemp(dir, "master_tmp_*.json")
	if err != nil {
		return err
	}
	tmpName := tmpFile.Name()

	if _, err := tmpFile.Write(data); err != nil {
		_ = tmpFile.Close()
		_ = os.Remove(tmpName)
		return err
	}
	if err := tmpFile.Sync(); err != nil {
		_ = tmpFile.Close()
		_ = os.Remove(tmpName)
		return err
	}
	if err := tmpFile.Close(); err != nil {
		_ = os.Remove(tmpName)
		return err
	}

	return os.Rename(tmpName, destPath)
}

// Keep only the last 20 history files
func (app *ServerApp) cleanHistory() {
	historyDir := filepath.Join(app.cfg.DataDir, "history")
	entries, err := os.ReadDir(historyDir)
	if err != nil {
		return
	}

	var jsonFiles []os.DirEntry
	for _, e := range entries {
		if !e.IsDir() && strings.HasPrefix(e.Name(), "master_") && strings.HasSuffix(e.Name(), ".json") {
			jsonFiles = append(jsonFiles, e)
		}
	}

	if len(jsonFiles) <= MaxHistoryKeep {
		return
	}

	// Sort lexicographically by name (timestamp format ensures correct chronological order)
	sort.Slice(jsonFiles, func(i, j int) bool {
		return jsonFiles[i].Name() < jsonFiles[j].Name()
	})

	// Remove older files
	removeCount := len(jsonFiles) - MaxHistoryKeep
	for i := 0; i < removeCount; i++ {
		_ = os.Remove(filepath.Join(historyDir, jsonFiles[i].Name()))
	}
}

// Append to data/audit.csv (time, client IP, action, SKU count, file name)
func (app *ServerApp) appendAudit(clientIP, action string, skus int, filename string) {
	auditPath := filepath.Join(app.cfg.DataDir, "audit.csv")
	f, err := os.OpenFile(auditPath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
	if err != nil {
		return
	}
	defer f.Close()

	w := csv.NewWriter(f)
	record := []string{
		time.Now().Format("2006-01-02 15:04:05"),
		clientIP,
		action,
		strconv.Itoa(skus),
		filename,
	}
	_ = w.Write(record)
	w.Flush()
}

// Read last 50 audit entries
func (app *ServerApp) getRecentAudit(max int) [][]string {
	auditPath := filepath.Join(app.cfg.DataDir, "audit.csv")
	f, err := os.Open(auditPath)
	if err != nil {
		return nil
	}
	defer f.Close()

	r := csv.NewReader(f)
	records, err := r.ReadAll()
	if err != nil || len(records) == 0 {
		return nil
	}

	start := 0
	if len(records) > max {
		start = len(records) - max
	}
	recent := records[start:]

	// Reverse to show newest first
	reversed := make([][]string, len(recent))
	for i, j := 0, len(recent)-1; j >= 0; i, j = i+1, j-1 {
		reversed[i] = recent[j]
	}
	return reversed
}

// History version metadata
type HistoryItem struct {
	Filename string
	Date     string
	Skus     int
	DocName  string
	Size     string
}

func (app *ServerApp) getHistoryList() []HistoryItem {
	historyDir := filepath.Join(app.cfg.DataDir, "history")
	entries, err := os.ReadDir(historyDir)
	if err != nil {
		return nil
	}

	var list []HistoryItem
	for _, e := range entries {
		if !e.IsDir() && strings.HasPrefix(e.Name(), "master_") && strings.HasSuffix(e.Name(), ".json") {
			info, err := e.Info()
			if err != nil {
				continue
			}

			// Read file to parse SKU count and doc name
			content, err := os.ReadFile(filepath.Join(historyDir, e.Name()))
			skus := 0
			docName := e.Name()
			if err == nil {
				var d MasterDocument
				if json.Unmarshal(content, &d) == nil {
					skus = len(d.List)
					if d.Name != "" {
						docName = d.Name
					}
				}
			}

			sizeStr := fmt.Sprintf("%.1f KB", float64(info.Size())/1024.0)

			list = append(list, HistoryItem{
				Filename: e.Name(),
				Date:     info.ModTime().Format("2006-01-02 15:04:05"),
				Skus:     skus,
				DocName:  docName,
				Size:     sizeStr,
			})
		}
	}

	// Sort newest first
	sort.Slice(list, func(i, j int) bool {
		return list[i].Filename > list[j].Filename
	})
	return list
}

// GET /admin - Presentable corporate boardroom status page
func (app *ServerApp) handleAdmin(w http.ResponseWriter, r *http.Request) {
	app.mu.RLock()
	defer app.mu.RUnlock()

	uptime := time.Since(app.startTime).Round(time.Second).String()
	lanURLs := app.getLanURLs(app.cfg.Port)
	auditRows := app.getRecentAudit(50)
	historyRows := app.getHistoryList()

	skuCount := 0
	lastUpdate := "None"
	docName := "None"
	if app.currentDoc != nil {
		skuCount = len(app.currentDoc.List)
		lastUpdate = app.currentDoc.At
		docName = app.currentDoc.Name
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")

	html := fmt.Sprintf(`<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>VKL Server Administration & LAN Status</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif; }
    body { background-color: #F4F6F9; color: #1E293B; font-size: 13.5px; }
    header { background-color: #0B1F3A; color: #FFF; padding: 14px 28px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 6px rgba(0,0,0,0.12); }
    .title { font-size: 18px; font-weight: 600; letter-spacing: 0.2px; display:flex; align-items:center; gap:10px; }
    .badge { background: #4A7FB5; color: #FFF; font-size: 11px; padding: 3px 8px; border-radius: 4px; font-weight: 600; }
    .container { max-width: 1360px; margin: 24px auto; padding: 0 20px; }
    .grid-kpi { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }
    .kpi-card { background: #FFF; border: 1px solid #CBD5E1; border-radius: 6px; padding: 16px; border-top: 4px solid #4A7FB5; }
    .kpi-title { font-size: 11.5px; color: #64748B; font-weight: 600; text-transform: uppercase; }
    .kpi-val { font-size: 22px; font-weight: 700; color: #0B1F3A; margin-top: 6px; }
    .card { background: #FFF; border: 1px solid #CBD5E1; border-radius: 6px; padding: 20px; margin-bottom: 24px; }
    .card-head { font-size: 15px; font-weight: 600; color: #0B1F3A; margin-bottom: 14px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #E2E8F0; padding-bottom: 10px; }
    .table-box { overflow-x: auto; }
    table { width: 100%%; border-collapse: collapse; font-size: 12.5px; }
    th { background: #0B1F3A; color: #FFF; text-align: left; padding: 10px 12px; font-weight: 600; }
    td { padding: 9px 12px; border-bottom: 1px solid #E2E8F0; }
    tr:hover { background: #F8FAFC; }
    .btn { cursor: pointer; background: #4A7FB5; color: #FFF; border: none; padding: 5px 12px; border-radius: 4px; font-size: 12px; font-weight: 500; }
    .btn:hover { background: #386794; }
    .btn-outline { background: transparent; border: 1px solid #CBD5E1; color: #1E293B; }
    .btn-outline:hover { background: #F1F5F9; }
    .lan-pill { background: #EBF3FA; border: 1px solid #CBD5E1; padding: 6px 12px; border-radius: 5px; font-family: monospace; display: inline-flex; align-items: center; gap: 8px; margin: 4px 8px 4px 0; }
  </style>
</head>
<body>
  <header>
    <div class="title">
      <span>VKL Order Converter - LAN Administration</span>
      <span class="badge">Version %s</span>
    </div>
    <div>
      <a href="/" style="color:#FFF; text-decoration:none; background:#1E3A5F; padding:6px 14px; border-radius:4px; font-weight:500;">Open Web Tool</a>
    </div>
  </header>

  <div class="container">
    <div class="grid-kpi">
      <div class="kpi-card">
        <div class="kpi-title">Server Status</div>
        <div class="kpi-val" style="color:#16A34A;">Online</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">System Uptime</div>
        <div class="kpi-val">%s</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">LAN Listen Port</div>
        <div class="kpi-val">%d</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Shared Master SKUs</div>
        <div class="kpi-val">%d</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Active Master File</div>
        <div class="kpi-val" style="font-size:14px; margin-top:10px; overflow:hidden; text-overflow:ellipsis;">%s</div>
      </div>
    </div>

    <!-- LAN URLs -->
    <div class="card">
      <div class="card-head">
        <span>Office LAN Access URLs</span>
        <span style="font-size:12px; color:#64748B;">Any PC on the office network can open these in Chrome/Edge</span>
      </div>
      <div>`, AppVersion, uptime, app.cfg.Port, skuCount, docName)

	for _, u := range lanURLs {
		html += fmt.Sprintf(`
        <div class="lan-pill">
          <span>%s</span>
          <button class="btn" style="padding:2px 8px; font-size:11px;" onclick="copyURL('%s')">Copy</button>
        </div>`, u, u)
	}

	html += fmt.Sprintf(`
      </div>
    </div>

    <!-- How colleagues connect -->
    <div class="card" style="background:#F8FAFC; border-left: 4px solid #4A7FB5;">
      <div style="font-weight:600; font-size:13.5px; color:#0B1F3A; margin-bottom:6px;">How Colleagues Connect</div>
      <p style="font-size:12.5px; color:#475569; line-height:1.5;">
        1. Ensure colleagues are connected to the same office Wi-Fi or Ethernet switch.<br>
        2. Give them any of the URLs above (e.g. <code>%s</code>).<br>
        3. No software, Python, or plugins required on their PCs.<br>
        4. Customer order files are processed 100%% privately inside their browser session and never transmitted over the network.
      </p>
    </div>

    <!-- Master History -->
    <div class="card">
      <div class="card-head">
        <span>Master SKU Version History (Last 20 Automatic Backups)</span>
        <span style="font-size:12px; color:#64748B;">Last update: %s</span>
      </div>
      <div class="table-box">
        <table>
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Snapshot File</th>
              <th>SKU Count</th>
              <th>Original Name</th>
              <th>Size</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>`, lanURLs[0], lastUpdate)

	if len(historyRows) == 0 {
		html += `<tr><td colspan="6" style="text-align:center; padding:18px; color:#64748B;">No version snapshots saved yet. Upload a master to record history.</td></tr>`
	} else {
		for _, h := range historyRows {
			html += fmt.Sprintf(`
            <tr>
              <td>%s</td>
              <td><code>%s</code></td>
              <td><strong>%d</strong></td>
              <td>%s</td>
              <td>%s</td>
              <td>
                <a class="btn btn-outline" style="text-decoration:none; padding:3px 8px;" href="/admin/download?file=%s">Download</a>
                <button class="btn" style="padding:3px 8px;" onclick="restoreVersion('%s')">Restore</button>
              </td>
            </tr>`, h.Date, h.Filename, h.Skus, h.DocName, h.Size, h.Filename, h.Filename)
		}
	}

	html += `
          </tbody>
        </table>
      </div>
    </div>

    <!-- Audit Log -->
    <div class="card">
      <div class="card-head">
        <span>Recent Audit Entries (Last 50 Events)</span>
        <span style="font-size:12px; color:#64748B;">Appended to data/audit.csv</span>
      </div>
      <div class="table-box">
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Client IP</th>
              <th>Action</th>
              <th>SKU Count</th>
              <th>File Name</th>
            </tr>
          </thead>
          <tbody>`

	if len(auditRows) == 0 {
		html += `<tr><td colspan="5" style="text-align:center; padding:18px; color:#64748B;">No audit entries recorded yet.</td></tr>`
	} else {
		for _, r := range auditRows {
			countStr := "-"
			if len(r) > 3 && r[3] != "0" {
				countStr = r[3]
			}
			fname := "-"
			if len(r) > 4 && r[4] != "" {
				fname = r[4]
			}
			html += fmt.Sprintf(`
            <tr>
              <td>%s</td>
              <td><code>%s</code></td>
              <td><strong>%s</strong></td>
              <td>%s</td>
              <td>%s</td>
            </tr>`, r[0], r[1], r[2], countStr, fname)
		}
	}

	html += `
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <script>
    function copyURL(text) {
      navigator.clipboard.writeText(text).then(function() {
        alert('Copied URL to clipboard: ' + text);
      });
    }

    function restoreVersion(filename) {
      var pin = '';
      if (confirm('Restore SKU master to version ' + filename + '?')) {
        pin = prompt('Enter Server PIN (leave blank if no PIN is configured):') || '';
        fetch('/admin/restore?file=' + encodeURIComponent(filename), {
          method: 'POST',
          headers: { 'X-VKL-Pin': pin }
        }).then(function(res) {
          if (res.ok) {
            alert('Version restored successfully!');
            window.location.reload();
          } else {
            alert('Failed to restore version (check PIN or file).');
          }
        });
      }
    }
  </script>
</body>
</html>`

	_, _ = w.Write([]byte(html))
}

// POST /admin/restore?file=...
func (app *ServerApp) handleAdminRestore(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	clientIP := getClientIP(r)

	// PIN Verification
	if app.cfg.Pin != "" {
		reqPin := strings.TrimSpace(r.Header.Get("X-VKL-Pin"))
		if reqPin != app.cfg.Pin {
			app.appendAudit(clientIP, "RESTORE_AUTH_FAILED", 0, "")
			http.Error(w, `{"error":"Invalid PIN"}`, http.StatusUnauthorized)
			return
		}
	}

	fileName := filepath.Base(r.URL.Query().Get("file"))
	if fileName == "" || !strings.HasPrefix(fileName, "master_") || !strings.HasSuffix(fileName, ".json") {
		http.Error(w, "Invalid filename", http.StatusBadRequest)
		return
	}

	histPath := filepath.Join(app.cfg.DataDir, "history", fileName)
	data, err := os.ReadFile(histPath)
	if err != nil {
		http.Error(w, "Historical snapshot not found", http.StatusNotFound)
		return
	}

	var doc MasterDocument
	if err := json.Unmarshal(data, &doc); err != nil {
		http.Error(w, "Corrupted snapshot file", http.StatusInternalServerError)
		return
	}

	app.mu.Lock()
	defer app.mu.Unlock()

	masterPath := filepath.Join(app.cfg.DataDir, "master.json")
	if err := atomicWriteFile(masterPath, data); err != nil {
		http.Error(w, "Failed to write restored master", http.StatusInternalServerError)
		return
	}

	app.currentDoc = &doc
	app.rawDocBytes = data

	app.appendAudit(clientIP, "RESTORE_MASTER", len(doc.List), fileName)
	app.logMsg(fmt.Sprintf("Restored master from %s by %s", fileName, clientIP))

	w.WriteHeader(http.StatusOK)
	_, _ = w.Write([]byte(`{"ok":true,"message":"Restored successfully"}`))
}

// GET /admin/download?file=...
func (app *ServerApp) handleAdminDownload(w http.ResponseWriter, r *http.Request) {
	fileName := filepath.Base(r.URL.Query().Get("file"))
	if fileName == "" || !strings.HasPrefix(fileName, "master_") || !strings.HasSuffix(fileName, ".json") {
		http.Error(w, "Invalid filename", http.StatusBadRequest)
		return
	}

	histPath := filepath.Join(app.cfg.DataDir, "history", fileName)
	data, err := os.ReadFile(histPath)
	if err != nil {
		http.Error(w, "File not found", http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Content-Disposition", fmt.Sprintf("attachment; filename=%q", fileName))
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write(data)
}

// Extract client IP helper
func getClientIP(r *http.Request) string {
	forwarded := r.Header.Get("X-Forwarded-For")
	if forwarded != "" {
		parts := strings.Split(forwarded, ",")
		return strings.TrimSpace(parts[0])
	}
	ip, _, err := net.SplitHostPort(r.RemoteAddr)
	if err == nil {
		return ip
	}
	return r.RemoteAddr
}

// Log rotation: 5 MB size limit, keeps up to 5 backups (server.log.1, server.log.2, etc.)
func (app *ServerApp) initLogging() {
	app.logMu.Lock()
	defer app.logMu.Unlock()

	logPath := filepath.Join("logs", "server.log")
	info, err := os.Stat(logPath)
	if err == nil {
		app.logSize = info.Size()
		if app.logSize >= MaxLogFileSize {
			app.rotateLogFiles()
		}
	}

	f, err := os.OpenFile(logPath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
	if err == nil {
		app.logFile = f
	}
}

func (app *ServerApp) rotateLogFiles() {
	if app.logFile != nil {
		_ = app.logFile.Close()
		app.logFile = nil
	}

	base := filepath.Join("logs", "server.log")
	// Shift old backups: server.log.4 -> server.log.5, etc.
	for i := MaxLogFiles - 1; i >= 1; i-- {
		oldName := fmt.Sprintf("%s.%d", base, i)
		newName := fmt.Sprintf("%s.%d", base, i+1)
		_ = os.Rename(oldName, newName)
	}
	_ = os.Rename(base, fmt.Sprintf("%s.1", base))
	app.logSize = 0
}

func (app *ServerApp) logMsg(msg string) {
	app.logMu.Lock()
	defer app.logMu.Unlock()

	line := fmt.Sprintf("[%s] %s\n", time.Now().Format("2006-01-02 15:04:05"), msg)
	lineBytes := []byte(line)

	if app.logSize+int64(len(lineBytes)) >= MaxLogFileSize {
		app.rotateLogFiles()
		logPath := filepath.Join("logs", "server.log")
		f, err := os.OpenFile(logPath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
		if err == nil {
			app.logFile = f
		}
	}

	if app.logFile != nil {
		n, _ := app.logFile.Write(lineBytes)
		app.logSize += int64(n)
	}
}
