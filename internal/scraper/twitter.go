package scraper

import (
	"context"
	"encoding/json"
	"fmt"
	"regexp"
	"strings"
	"sync"
	"time"

	"github.com/gorilla/websocket"
	"go.uber.org/zap"
)

// ─── Twitter Scraper ───

type TwitterScraper struct {
	*BaseScraper
	client       *TwitterClient
	accounts     []string
	keywords     []regexp.Regexp
	accountRe    *regexp.Regexp
	keywordRe    *regexp.Regexp
}

type TwitterClient struct {
	bearerTokens []string
	currentToken int
	mu           sync.Mutex
	proxyPool    []string
	currentProxy int
}

func NewTwitterScraper(config ScraperConfig, logger *zap.Logger, publisher *Publisher) (*TwitterScraper, error) {
	base := NewBaseScraper("twitter", config, logger, publisher)
	
	client := &TwitterClient{
		bearerTokens: extractBearerTokens(config.Credentials),
		proxyPool:    config.ProxyPool,
	}

	keywords := config.Filters.Keywords
	if len(keywords) == 0 {
		keywords = defaultTwitterKeywords()
	}
	keywordPatterns := compileRegexps(keywords)

	accounts := config.Filters.Accounts
	if len(accounts) == 0 {
		accounts = defaultTwitterAccounts()
	}
	accountPattern := compileAccountRegexp(accounts)

	return &TwitterScraper{
		BaseScraper:  base,
		client:       client,
		accounts:     accounts,
		keywords:     keywordPatterns,
		accountRe:    accountPattern,
		keywordRe:    keywordPatterns[0], // primary
	}, nil
}

func (t *TwitterScraper) Start(ctx context.Context) error {
	t.logger.Info("starting twitter scraper", zap.Int("accounts", len(t.accounts)), zap.Int("keywords", len(t.keywords)))

	// Start heartbeat
	go t.heartbeat(ctx)

	// Start timeline polling for each account
	for _, account := range t.accounts {
		t.wg.Add(1)
		go t.pollAccountTimeline(ctx, account)
	}

	// Start keyword search polling
	t.wg.Add(1)
	go t.pollKeywordSearch(ctx)

	// Start mention polling
	t.wg.Add(1)
	go t.pollMentions(ctx)

	return nil
}

func (t *TwitterScraper) Stop() error {
	close(t.stopChan)
	t.wg.Wait()
	return nil
}

func (t *TwitterScraper) pollAccountTimeline(ctx context.Context, account string) {
	defer t.wg.Done()

	ticker := time.NewTicker(t.config.PollInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-t.stopChan:
			return
		case <-ticker.C:
			if err := t.fetchAndPublish(ctx, account); err != nil {
				t.recordError(err)
			}
		}
	}
}

func (t *TwitterScraper) fetchAndPublish(ctx context.Context, account string) error {
	if err := t.waitForRateLimit(ctx); err != nil {
		return err
	}

	tweets, err := t.client.FetchUserTweets(ctx, account, 20)
	if err != nil {
		return fmt.Errorf("fetch tweets for %s: %w", account, err)
	}

	for _, tweet := range tweets {
		if t.isRelevant(tweet) {
			event := RawEvent{
				ID:          fmt.Sprintf("evt_tw_%s_%d", account, tweet.ID),
				Source:      "twitter",
				SourceID:    fmt.Sprintf("%d", tweet.ID),
				Type:        "announcement",
				CollectedAt: time.Now(),
				Raw:         tweet.Raw,
				Metadata: map[string]interface{}{
					"author":      tweet.Author,
					"author_id":   tweet.AuthorID,
					"url":         tweet.URL,
					"retweets":    tweet.RetweetCount,
					"likes":       tweet.LikeCount,
					"replies":     tweet.ReplyCount,
				},
				Confidence: t.calculateConfidence(tweet),
			}
			if err := t.publishEvent(ctx, event); err != nil {
				t.logger.Error("publish failed", zap.Error(err))
			} else {
				t.recordEvent()
			}
		}
	}
	return nil
}

func (t *TwitterScraper) pollKeywordSearch(ctx context.Context) {
	defer t.wg.Done()
	ticker := time.NewTicker(t.config.PollInterval * 3)
	defer ticker.Stop()

	keywords := []string{"airdrop", "claim", "token launch", "farming", "retroactive", "TGE", "genesis drop"}
	
	for {
		select {
		case <-ctx.Done():
			return
		case <-t.stopChan:
			return
		case <-ticker.C:
			for _, kw := range keywords {
				if err := t.waitForRateLimit(ctx); err != nil {
					continue
				}
				tweets, err := t.client.SearchTweets(ctx, kw, 50)
				if err != nil {
					t.recordError(err)
					continue
				}
				for _, tweet := range tweets {
					if t.isRelevant(tweet) {
						event := RawEvent{
							ID:          fmt.Sprintf("evt_tw_kw_%s_%d", kw, tweet.ID),
							Source:      "twitter",
							SourceID:    fmt.Sprintf("%d", tweet.ID),
							Type:        "mention",
							CollectedAt: time.Now(),
							Raw:         tweet.Raw,
							Metadata: map[string]interface{}{
								"keyword":     kw,
								"author":      tweet.Author,
								"url":         tweet.URL,
								"retweets":    tweet.RetweetCount,
								"likes":       tweet.LikeCount,
							},
							Confidence: t.calculateConfidence(tweet),
						}
						t.publishEvent(ctx, event)
						t.recordEvent()
					}
				}
			}
		}
	}
}

func (t *TwitterScraper) pollMentions(ctx context.Context) {
	defer t.wg.Done()
	// Implementation for mention polling
	ticker := time.NewTicker(t.config.PollInterval * 5)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-t.stopChan:
			return
		case <-ticker.C:
			// Poll mentions for tracked accounts
		}
	}
}

func (t *TwitterScraper) isRelevant(tweet Tweet) bool {
	text := strings.ToLower(tweet.Text)
	
	// Check account
	if t.accountRe.MatchString(tweet.Author) {
		return true
	}
	
	// Check keywords
	for _, re := range t.keywords {
		if re.MatchString(text) {
			return true
		}
	}
	
	// Check engagement
	if tweet.RetweetCount + tweet.LikeCount < t.config.Filters.MinEngagement {
		return false
	}
	
	return false
}

func (t *TwitterScraper) calculateConfidence(tweet Tweet) float64 {
	confidence := 0.5
	
	// Known account boost
	if t.accountRe.MatchString(tweet.Author) {
		confidence += 0.2
	}
	
	// Keyword matches
	matches := 0
	text := strings.ToLower(tweet.Text)
	for _, re := range t.keywords {
		if re.MatchString(text) {
			matches++
		}
	}
	confidence += float64(matches) * 0.1
	
	// Engagement
	engagement := tweet.RetweetCount + tweet.LikeCount
	if engagement > 1000 {
		confidence += 0.15
	} else if engagement > 100 {
		confidence += 0.1
	}
	
	// Media presence
	if len(tweet.Media) > 0 {
		confidence += 0.05
	}
	
	return min(confidence, 1.0)
}

// ─── Types ───

type Tweet struct {
	ID            int64
	Text          string
	Author        string
	AuthorID      string
	URL           string
	RetweetCount  int
	LikeCount     int
	ReplyCount    int
	Media         []Media
	Raw           json.RawMessage
	CreatedAt     time.Time
}

type Media struct {
	Type string `json:"type"`
	URL  string `json:"url"`
}

// ─── Twitter Client (Simplified) ───

func (c *TwitterClient) FetchUserTweets(ctx context.Context, username string, count int) ([]Tweet, error) {
	// In production: Use Twitter API v2 with bearer token rotation
	// GET /2/users/by/username/:username/tweets
	return []Tweet{}, nil
}

func (c *TwitterClient) SearchTweets(ctx context.Context, query string, count int) ([]Tweet, error) {
	// GET /2/tweets/search/recent
	return []Tweet{}, nil
}

func (c *TwitterClient) getNextToken() string {
	c.mu.Lock()
	defer c.mu.Unlock()
	token := c.bearerTokens[c.currentToken]
	c.currentToken = (c.currentToken + 1) % len(c.bearerTokens)
	return token
}

// ─── Helpers ───

func extractBearerTokens(creds []Credential) []string {
	var tokens []string
	for _, c := range creds {
		if c.Type == "bearer_token" {
			tokens = append(tokens, c.Value)
		}
	}
	return tokens
}

func compileRegexps(patterns []string) []*regexp.Regexp {
	var res []*regexp.Regexp
	for _, p := range patterns {
		if re, err := regexp.Compile("(?i)" + p); err == nil {
			res = append(res, re)
		}
	}
	return res
}

func compileAccountRegexp(accounts []string) *regexp.Regexp {
	if len(accounts) == 0 {
		return regexp.MustCompile("(?i)^$") // never matches
	}
	patterns := make([]string, len(accounts))
	for i, a := range accounts {
		patterns[i] = regexp.QuoteMeta(a)
	}
	return regexp.MustCompile("(?i)^(" + strings.Join(patterns, "|") + ")$")
}

func defaultTwitterKeywords() []string {
	return []string{
		`airdrop`,
		`claim\s+(your\s+)?(tokens?|rewards?)`,
		`retroactive`,
		`token\s+(launch|distribution|generation)`,
		`TGE`,
		`farming\s+(opportunity|season)`,
		`genesis\s+(drop|reward)`,
		`governance\s+token`,
		`incentivized\s+testnet`,
		`mainnet\s+launch`,
	}
}

func defaultTwitterAccounts() []string {
	return []string{
		"airdrops_io", "DefiLlama", "LayerZero_Fndn", "zksync", "arbitrum",
		"optimismFND", "base", "starknet", "scroll_zkp", "linea_build",
		"MantaNetwork", "blast_l2", "mode_network", "berachain", "monad_xyz",
		"initia_labs", "eigenlayer", "celestiaorg", "suinft", "aptoslabs",
	}
}

func min(a, b float64) float64 {
	if a < b {
		return a
	}
	return b
}