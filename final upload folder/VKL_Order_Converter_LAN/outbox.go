package main

import (
	"crypto/rand"
	"encoding/hex"
	"io"
	"net/http"
	"strconv"
	"strings"
	"sync"
	"time"
)

// Outbox: short-lived (10 minutes, memory only) hand-over of a generated
// Excel file from the user's browser to the Outlook helper on the same PC.
const (
	outboxMaxBytes = 10 * 1024 * 1024
	outboxTTL      = 10 * time.Minute
	outboxMaxItems = 200
)

type outboxItem struct {
	data []byte
	name string
	exp  time.Time
}

var (
	outboxMu    sync.Mutex
	outboxItems = map[string]outboxItem{}
)

func outboxPurge() {
	now := time.Now()
	for k, v := range outboxItems {
		if now.After(v.exp) {
			delete(outboxItems, k)
		}
	}
}

func safeName(s string) string {
	var b strings.Builder
	for _, r := range s {
		if r < 32 || strings.ContainsRune(`\/:*?"<>|`, r) {
			continue
		}
		b.WriteRune(r)
	}
	out := strings.TrimSpace(b.String())
	if out == "" || len(out) > 150 {
		out = "VKL_Report.xlsx"
	}
	return out
}

// POST /api/outbox?name=file.xlsx  -> {"id":"..."}
// GET  /api/outbox/<id>            -> file bytes (X-Filename header)
func (app *ServerApp) handleOutbox(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Cache-Control", "no-store")
	if r.Method == http.MethodPost && r.URL.Path == "/api/outbox" {
		body, err := io.ReadAll(http.MaxBytesReader(w, r.Body, outboxMaxBytes))
		if err != nil || len(body) < 4 || body[0] != 'P' || body[1] != 'K' {
			http.Error(w, "expected an .xlsx file up to 10 MB", http.StatusBadRequest)
			return
		}
		raw := make([]byte, 16)
		if _, err := rand.Read(raw); err != nil {
			http.Error(w, "random failure", http.StatusInternalServerError)
			return
		}
		id := hex.EncodeToString(raw)
		outboxMu.Lock()
		outboxPurge()
		if len(outboxItems) >= outboxMaxItems {
			outboxMu.Unlock()
			http.Error(w, "outbox busy, try again", http.StatusServiceUnavailable)
			return
		}
		outboxItems[id] = outboxItem{data: body, name: safeName(r.URL.Query().Get("name")), exp: time.Now().Add(outboxTTL)}
		outboxMu.Unlock()
		app.logMsg("OUTBOX stored " + strconv.Itoa(len(body)) + " bytes from " + r.RemoteAddr)
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"id":"` + id + `"}`))
		return
	}
	if r.Method == http.MethodGet && strings.HasPrefix(r.URL.Path, "/api/outbox/") {
		id := strings.TrimPrefix(r.URL.Path, "/api/outbox/")
		outboxMu.Lock()
		outboxPurge()
		it, ok := outboxItems[id]
		outboxMu.Unlock()
		if !ok {
			http.Error(w, "expired or unknown", http.StatusNotFound)
			return
		}
		w.Header().Set("Content-Type", "application/octet-stream")
		w.Header().Set("X-Filename", it.name)
		_, _ = w.Write(it.data)
		return
	}
	http.Error(w, "not found", http.StatusNotFound)
}
