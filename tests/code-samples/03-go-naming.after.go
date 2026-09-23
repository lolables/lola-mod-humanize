// Package auth handles user authentication over HTTP.
package auth

import (
	"encoding/json"
	"log"
	"net/http"
	"strings"
	"sync"
	"time"
)

type DBPool struct {
	maxConns    int
	activeConns int
	mu          sync.Mutex
}

func NewDBPool(max int) *DBPool {
	return &DBPool{maxConns: max}
}

type AuthHandler struct {
	db      *DBPool
	timeout time.Duration
}

func NewAuthHandler(db *DBPool, timeout time.Duration) *AuthHandler {
	return &AuthHandler{db: db, timeout: timeout}
}

// ServeHTTP handles POST /auth requests.
func (h *AuthHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "use POST", http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		Username string `json:"username"`
		Password string `json:"password"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "bad json", http.StatusBadRequest)
		return
	}

	if strings.TrimSpace(req.Username) == "" {
		http.Error(w, "username required", http.StatusBadRequest)
		return
	}

	log.Printf("auth attempt: %s", req.Username)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]any{
		"authenticated": true,
	})
}

// RequireJSON rejects requests without a JSON content type.
func RequireJSON(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("Content-Type") != "application/json" {
			http.Error(w, "need application/json", http.StatusUnsupportedMediaType)
			return
		}
		next.ServeHTTP(w, r)
	})
}
