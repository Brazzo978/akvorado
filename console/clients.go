// SPDX-FileCopyrightText: 2026 Akvorado contributors
// SPDX-License-Identifier: AGPL-3.0-only

package console

import (
	"net/http"
	"net/netip"
	"strings"
	"time"

	"akvorado/common/helpers"
	"akvorado/common/httpserver"
)

const clientPageSize = 25

type clientTrafficInput struct {
	Start    time.Time      `json:"start" validate:"required"`
	End      time.Time      `json:"end" validate:"required,gtfield=Start"`
	Prefixes []netip.Prefix `json:"prefixes" validate:"max=16"`
	IP       netip.Addr     `json:"ip"`
	Sort     string         `json:"sort" validate:"omitempty,oneof=total download upload"`
	Offset   uint32         `json:"offset" validate:"max=1000000"`
}

type clientTrafficVolume struct {
	Download uint64 `json:"download" ch:"download"`
	Upload   uint64 `json:"upload" ch:"upload"`
}

type clientTrafficRow struct {
	IP string `json:"ip" ch:"ip"`
	clientTrafficVolume
}

type clientTrafficBreakdown struct {
	ID   uint32 `json:"id" ch:"id"`
	Name string `json:"name" ch:"name"`
	clientTrafficVolume
}

type clientTrafficPoint struct {
	Time uint32 `json:"time" ch:"period"`
	clientTrafficVolume
}

// Store a flow against its endpoint on the internal interface. Restrict it to
// externally routed traffic and omit the router's own traffic (missing interface).
const clientTrafficSource = `
WITH InIfBoundary = 'internal' AS outbound,
     if(outbound, SrcAddr, DstAddr) AS client_ip,
     toUInt64(Bytes) * toUInt64(SamplingRate) AS bytes_sampled
SELECT %s,
       sumIf(bytes_sampled, NOT outbound) AS download,
       sumIf(bytes_sampled, outbound) AS upload
FROM flows
WHERE TimeReceived >= toDateTime(?, 'UTC') AND TimeReceived < toDateTime(?, 'UTC')
  AND InIfName != '' AND OutIfName != ''
  AND ((outbound AND OutIfBoundary = 'external')
    OR (InIfBoundary = 'external' AND OutIfBoundary = 'internal'))
`

func (input clientTrafficInput) scope() (string, []any) {
	args := []any{input.Start.UTC().Format("2006-01-02 15:04:05"), input.End.UTC().Format("2006-01-02 15:04:05")}
	scope := ""
	if len(input.Prefixes) > 0 {
		placeholders := make([]string, 0, len(input.Prefixes))
		for _, prefix := range input.Prefixes {
			placeholders = append(placeholders, "?")
			args = append(args, helpers.PrefixTo6(prefix.Masked()).String())
		}
		scope += "  AND arrayExists(cidr -> isIPAddressInRange(toString(client_ip), cidr), [" +
			strings.Join(placeholders, ", ") + "])\n"
	}
	if input.IP.IsValid() {
		scope += "  AND client_ip = toIPv6(?)\n"
		args = append(args, input.IP.WithZone("").Unmap().String())
	}
	return scope, args
}

func readClientTrafficInput(w http.ResponseWriter, req *http.Request) (clientTrafficInput, bool) {
	var input clientTrafficInput
	if err := httpserver.BindJSON(req, &input); err != nil {
		httpserver.WriteJSON(w, http.StatusBadRequest, helpers.M{"message": "Parametri della richiesta non validi."})
		return input, false
	}
	if input.End.Sub(input.Start) > 24*time.Hour ||
		!input.Start.Equal(input.Start.Truncate(time.Minute)) ||
		!input.End.Equal(input.End.Truncate(time.Minute)) {
		httpserver.WriteJSON(w, http.StatusBadRequest, helpers.M{"message": "Scegli un intervallo fino a 24 ore, con precisione al minuto."})
		return input, false
	}
	for _, prefix := range input.Prefixes {
		if !prefix.IsValid() {
			httpserver.WriteJSON(w, http.StatusBadRequest, helpers.M{"message": "Inserisci le subnet in formato CIDR."})
			return input, false
		}
	}
	return input, true
}

func (c *Component) queryClientTraffic(w http.ResponseWriter, req *http.Request, out any, sql string, args ...any) bool {
	c.metrics.clickhouseQueries.WithLabelValues("flows").Inc()
	if err := c.d.ClickHouseDB.Select(c.t.Context(req.Context()), out, sql, args...); err != nil {
		c.r.Err(err).Msg("unable to query client traffic")
		httpserver.WriteJSON(w, http.StatusInternalServerError, helpers.M{"message": "Impossibile caricare il traffico dei clienti."})
		return false
	}
	return true
}

func (c *Component) clientTrafficHandlerFunc(w http.ResponseWriter, req *http.Request) {
	input, ok := readClientTrafficInput(w, req)
	if !ok {
		return
	}
	scope, args := input.scope()
	order := "(download + upload)"
	switch input.Sort {
	case "download":
		order = "download"
	case "upload":
		order = "upload"
	}
	query := strings.Replace(clientTrafficSource, "%s", "replaceRegexpOne(toString(client_ip), '^::ffff:', '') AS ip", 1) +
		scope + "GROUP BY client_ip ORDER BY " + order + " DESC, client_ip LIMIT ? OFFSET ?"
	rows := []clientTrafficRow{}
	if !c.queryClientTraffic(w, req, &rows, query, append(args, clientPageSize+1, input.Offset)...) {
		return
	}
	hasMore := len(rows) > clientPageSize
	if hasMore {
		rows = rows[:clientPageSize]
	}
	httpserver.WriteJSON(w, http.StatusOK, helpers.M{"rows": rows, "hasMore": hasMore})
}

func (c *Component) clientDetailHandlerFunc(w http.ResponseWriter, req *http.Request) {
	input, ok := readClientTrafficInput(w, req)
	if !ok {
		return
	}
	if !input.IP.IsValid() {
		httpserver.WriteJSON(w, http.StatusBadRequest, helpers.M{"message": "Inserisci un indirizzo IP valido."})
		return
	}
	scope, args := input.scope()
	points := []clientTrafficPoint{}
	query := strings.Replace(clientTrafficSource, "%s", "toUnixTimestamp(toStartOfMinute(TimeReceived)) AS period", 1) +
		scope + "GROUP BY period ORDER BY period"
	if !c.queryClientTraffic(w, req, &points, query, args...) {
		return
	}

	protocols := []clientTrafficBreakdown{}
	networks := []clientTrafficBreakdown{}
	for _, breakdown := range []struct {
		id, dictionary string
		out            *[]clientTrafficBreakdown
	}{
		{"Proto", "protocols", &protocols},
		{"if(outbound, DstAS, SrcAS)", "asns", &networks},
	} {
		query := strings.Replace(clientTrafficSource, "%s", breakdown.id+" AS id", 1) +
			scope + "GROUP BY id ORDER BY (download + upload) DESC, id LIMIT 20"
		query = "SELECT id, dictGetOrDefault(?, 'name', id, '') AS name, download, upload FROM (" + query + ") " +
			"ORDER BY (download + upload) DESC, id"
		queryArgs := append([]any{c.d.ClickHouseDB.DatabaseName() + "." + breakdown.dictionary}, args...)
		if !c.queryClientTraffic(w, req, breakdown.out, query, queryArgs...) {
			return
		}
	}

	total := clientTrafficVolume{}
	peak := clientTrafficVolume{}
	for _, point := range points {
		total.Download += point.Download
		total.Upload += point.Upload
		peak.Download = max(peak.Download, point.Download)
		peak.Upload = max(peak.Upload, point.Upload)
	}
	httpserver.WriteJSON(w, http.StatusOK, helpers.M{
		"points": points, "protocols": protocols, "networks": networks,
		"total": total, "peakDownloadBps": float64(peak.Download) * 8 / 60, "peakUploadBps": float64(peak.Upload) * 8 / 60,
	})
}
