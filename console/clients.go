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

const (
	clientPageSize     = 25
	clientHistoryTable = "flows_clients_hourly"
	clientHistoryLimit = 60 * 24 * time.Hour
)

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

const clientHistorySource = `
WITH ClientIP AS client_ip
SELECT %s, sum(Download) AS download, sum(Upload) AS upload
FROM flows_clients_hourly
WHERE Hour >= toDateTime(?, 'UTC') AND Hour < toDateTime(?, 'UTC')
`

func (input clientTrafficInput) usesHistory() bool {
	return input.End.Sub(input.Start) > 24*time.Hour
}

func (input clientTrafficInput) source(selectExpr string) string {
	source := clientTrafficSource
	if input.usesHistory() {
		source = clientHistorySource
	}
	return strings.Replace(source, "%s", selectExpr, 1)
}

type clientHistoryCoverage struct {
	Start *time.Time `ch:"oldest" json:"start"`
	End   *time.Time `ch:"latest" json:"end"`
}

func (c *Component) clientCoverage(w http.ResponseWriter, req *http.Request, input clientTrafficInput) (*clientHistoryCoverage, bool) {
	if !input.usesHistory() {
		return nil, true
	}
	var coverage []clientHistoryCoverage
	const query = "SELECT minOrNull(Hour) AS oldest, addHours(maxOrNull(Hour), 1) AS latest FROM flows_clients_hourly"
	if !c.queryClientTraffic(w, req, input, &coverage, query) {
		return nil, false
	}
	return &coverage[0], true
}

func (input clientTrafficInput) scope() (string, []any) {
	args := []any{input.Start.UTC().Format("2006-01-02 15:04:05"), input.End.UTC().Format("2006-01-02 15:04:05")}
	scope := ""
	if len(input.Prefixes) > 0 {
		placeholders := make([]string, 0, len(input.Prefixes))
		for _, prefix := range input.Prefixes {
			placeholders = append(placeholders, "IPv6CIDRToRange(toIPv6(?), ?)")
			prefix = helpers.PrefixTo6(prefix.Masked())
			args = append(args, prefix.Addr().String(), prefix.Bits())
		}
		scope += "  AND arrayExists(bounds -> client_ip BETWEEN bounds.1 AND bounds.2, [" +
			strings.Join(placeholders, ", ") + "])\n"
	}
	if input.IP.IsValid() {
		scope += "  AND client_ip = toIPv6(?)\n"
		args = append(args, input.IP.WithZone("").Unmap().String())
	}
	return scope, args
}

func (c *Component) readClientTrafficInput(w http.ResponseWriter, req *http.Request) (clientTrafficInput, bool) {
	var input clientTrafficInput
	if err := httpserver.BindJSON(req, &input); err != nil {
		httpserver.WriteJSON(w, http.StatusBadRequest, helpers.M{"message": "Parametri della richiesta non validi."})
		return input, false
	}
	bucket := time.Minute
	if input.usesHistory() {
		if !c.config.ClientHistory || input.End.Sub(input.Start) > clientHistoryLimit {
			httpserver.WriteJSON(w, http.StatusBadRequest, helpers.M{"message": "The selected range exceeds the available history window."})
			return input, false
		}
		bucket = time.Hour
	}
	if !input.Start.Equal(input.Start.Truncate(bucket)) ||
		!input.End.Equal(input.End.Truncate(bucket)) {
		httpserver.WriteJSON(w, http.StatusBadRequest, helpers.M{"message": "Align the time range to full measurement intervals."})
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

func (c *Component) queryClientTraffic(w http.ResponseWriter, req *http.Request, input clientTrafficInput, out any, sql string, args ...any) bool {
	table := "flows"
	if input.usesHistory() {
		table = clientHistoryTable
	}
	c.metrics.clickhouseQueries.WithLabelValues(table).Inc()
	if err := c.d.ClickHouseDB.Select(c.t.Context(req.Context()), out, sql, args...); err != nil {
		c.r.Err(err).Msg("unable to query client traffic")
		httpserver.WriteJSON(w, http.StatusInternalServerError, helpers.M{"message": "Impossibile caricare il traffico dei clienti."})
		return false
	}
	return true
}

func (c *Component) clientTrafficHandlerFunc(w http.ResponseWriter, req *http.Request) {
	input, ok := c.readClientTrafficInput(w, req)
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
	query := input.source("replaceRegexpOne(toString(client_ip), '^::ffff:', '') AS ip") +
		scope + "GROUP BY client_ip ORDER BY " + order + " DESC, client_ip LIMIT ? OFFSET ?"
	rows := []clientTrafficRow{}
	if !c.queryClientTraffic(w, req, input, &rows, query, append(args, clientPageSize+1, input.Offset)...) {
		return
	}
	hasMore := len(rows) > clientPageSize
	if hasMore {
		rows = rows[:clientPageSize]
	}
	coverage, ok := c.clientCoverage(w, req, input)
	if !ok {
		return
	}
	httpserver.WriteJSON(w, http.StatusOK, helpers.M{"rows": rows, "hasMore": hasMore, "coverage": coverage})
}

func (c *Component) clientDetailHandlerFunc(w http.ResponseWriter, req *http.Request) {
	input, ok := c.readClientTrafficInput(w, req)
	if !ok {
		return
	}
	if !input.IP.IsValid() {
		httpserver.WriteJSON(w, http.StatusBadRequest, helpers.M{"message": "Inserisci un indirizzo IP valido."})
		return
	}
	scope, args := input.scope()
	points := []clientTrafficPoint{}
	bucketSeconds := 60
	timeColumn := "toStartOfMinute(TimeReceived)"
	remoteAS := "if(outbound, DstAS, SrcAS)"
	if input.usesHistory() {
		bucketSeconds = 3600
		timeColumn = "Hour"
		remoteAS = "RemoteAS"
	}
	query := input.source("toUnixTimestamp("+timeColumn+") AS period") + scope + "GROUP BY period ORDER BY period"
	if !c.queryClientTraffic(w, req, input, &points, query, args...) {
		return
	}

	protocols := []clientTrafficBreakdown{}
	networks := []clientTrafficBreakdown{}
	for _, breakdown := range []struct {
		id, dictionary string
		out            *[]clientTrafficBreakdown
	}{
		{"Proto", "protocols", &protocols},
		{remoteAS, "asns", &networks},
	} {
		query := input.source(breakdown.id+" AS id") +
			scope + "GROUP BY id ORDER BY (download + upload) DESC, id LIMIT 20"
		query = "SELECT id, dictGetOrDefault(?, 'name', id, '') AS name, download, upload FROM (" + query + ") " +
			"ORDER BY (download + upload) DESC, id"
		queryArgs := append([]any{c.d.ClickHouseDB.DatabaseName() + "." + breakdown.dictionary}, args...)
		if !c.queryClientTraffic(w, req, input, breakdown.out, query, queryArgs...) {
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
	coverage, ok := c.clientCoverage(w, req, input)
	if !ok {
		return
	}
	httpserver.WriteJSON(w, http.StatusOK, helpers.M{
		"points": points, "protocols": protocols, "networks": networks,
		"coverage": coverage, "bucketSeconds": bucketSeconds,
		"total": total, "peakDownloadBps": float64(peak.Download) * 8 / float64(bucketSeconds),
		"peakUploadBps": float64(peak.Upload) * 8 / float64(bucketSeconds),
	})
}
