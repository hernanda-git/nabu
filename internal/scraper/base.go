package scraper

import (
	"context"
	"encoding/json"
	"fmt"
	"sync"
	"time"

	amqp "github.com/rabbitmq/amqp091-go"
	"github.com/redis/go-redis/v9"
	"go.uber.org/zap"
)

// ─── Types ───

type RawEvent struct {
	ID           string                 `json:"id"`
	Source       string                 `json:"source"`
	SourceID     string                 `json:"source_id"`
	Type         string                 `json:"type"`
	CollectedAt  time.Time              `json:"collected_at"`
	Raw          json.RawMessage        `json:"raw"`
	Metadata     map[string]interface{} `json:"metadata"`
	Confidence   float64                `json:"confidence"`
}

type ScraperConfig struct {
	SourceType     string        `yaml:"source_type"`
	Enabled        bool          `yaml:"enabled"`
	PollInterval   time.Duration `yaml:"poll_interval"`
	RateLimit      RateLimitConfig `yaml:"rate_limit"`
	Credentials    []Credential  `yaml:"credentials"`
	ProxyPool      []string      `yaml:"proxy_pool"`
	Filters        FilterConfig  `yaml:"filters"`
	MaxConcurrency int           `yaml:"max_concurrency"`
	BatchSize      int           `yaml:"batch_size"`
}

type RateLimitConfig struct {
	MaxPerWindow int           `yaml:"max_per_window"`
	Window       time.Duration `yaml:"window"`
	Burst        int           `yaml:"burst"`
}

type Credential struct {
	Type  string `yaml:"type"`
	Value string `yaml:"value"`
}

type FilterConfig struct {
	Keywords     []string `yaml:"keywords"`
	Accounts     []string `yaml:"accounts"`
	MinEngagement int     `yaml:"min_engagement"`
	Languages    []string `yaml:"languages"`
}

type Scraper interface {
	Name() string
	Start(ctx context.Context) error
	Stop() error
	Health() HealthStatus
	Config() ScraperConfig
}

type HealthStatus struct {
	Healthy    bool      `json:"healthy"`
	LastEvent  time.Time `json:"last_event"`
	EventsCount int64    `json:"events_count"`
	Errors     int64     `json:"errors"`
	LastError  string    `json:"last_error,omitempty"`
}

// ─── Base Scraper ───

type BaseScraper struct {
	name       string
	config     ScraperConfig
	logger     *zap.Logger
	publisher  *Publisher
	rateLimiter *TokenBucket
	health     HealthStatus
	mu         sync.RWMutex
	stopChan   chan struct{}
	wg         sync.WaitGroup
}

func NewBaseScraper(name string, config ScraperConfig, logger *zap.Logger, publisher *Publisher) *BaseScraper {
	return &BaseScraper{
		name:       name,
		config:     config,
		logger:     logger.Named(name),
		publisher:  publisher,
		rateLimiter: NewTokenBucket(config.RateLimit.MaxPerWindow, config.RateLimit.Window, config.RateLimit.Burst),
		stopChan:   make(chan struct{}),
	}
}

func (b *BaseScraper) Name() string       { return b.name }
func (b *BaseScraper) Config() ScraperConfig { return b.config }
func (b *BaseScraper) Health() HealthStatus {
	b.mu.RLock()
	defer b.mu.RUnlock()
	return b.health
}

func (b *BaseScraper) updateHealth(fn func(*HealthStatus)) {
	b.mu.Lock()
	defer b.mu.Unlock()
	fn(&b.health)
}

func (b *BaseScraper) recordEvent() {
	b.updateHealth(func(h *HealthStatus) {
		h.LastEvent = time.Now()
		h.EventsCount++
		h.Healthy = true
	})
}

func (b *BaseScraper) recordError(err error) {
	b.updateHealth(func(h *HealthStatus) {
		h.Errors++
		h.LastError = err.Error()
		if h.Errors > 10 {
			h.Healthy = false
		}
	})
	b.logger.Error("scraper error", zap.Error(err))
}

func (b *BaseScraper) publishEvent(ctx context.Context, event RawEvent) error {
	body, err := json.Marshal(event)
	if err != nil {
		return fmt.Errorf("marshal event: %w", err)
	}

	return b.publisher.Publish(ctx, "raw_events", body)
}

func (b *BaseScraper) heartbeat(ctx context.Context) {
	ticker := time.NewTicker(15 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-b.stopChan:
			return
		case <-ticker.C:
			b.publisher.PublishHeartbeat(ctx, b.name)
		}
	}
}

func (b *BaseScraper) waitForRateLimit(ctx context.Context) error {
	return b.rateLimiter.Take(ctx)
}

// ─── Publisher ───

type Publisher struct {
	conn    *amqp.Connection
	channel *amqp.Channel
	logger  *zap.Logger
	mu      sync.Mutex
}

func NewPublisher(url string, logger *zap.Logger) (*Publisher, error) {
	conn, err := amqp.Dial(url)
	if err != nil {
		return nil, fmt.Errorf("dial rabbitmq: %w", err)
	}

	ch, err := conn.Channel()
	if err != nil {
		conn.Close()
		return nil, fmt.Errorf("open channel: %w", err)
	}

	// Declare exchanges and queues
	if err := ch.ExchangeDeclare("raw_events", "topic", true, false, false, false, nil); err != nil {
		ch.Close()
		conn.Close()
		return nil, fmt.Errorf("declare exchange: %w", err)
	}

	if _, err := ch.QueueDeclare("raw_events", true, false, false, false, nil); err != nil {
		ch.Close()
		conn.Close()
		return nil, fmt.Errorf("declare queue: %w", err)
	}

	if err := ch.QueueBind("raw_events", "raw_events", "raw_events", false, nil); err != nil {
		ch.Close()
		conn.Close()
		return nil, fmt.Errorf("bind queue: %w", err)
	}

	// Heartbeat exchange
	if err := ch.ExchangeDeclare("scraper_heartbeats", "topic", true, false, false, false, nil); err != nil {
		ch.Close()
		conn.Close()
		return nil, fmt.Errorf("declare heartbeat exchange: %w", err)
	}

	p := &Publisher{
		conn:    conn,
		channel: ch,
		logger:  logger.Named("publisher"),
	}

	go p.reconnectLoop()
	return p, nil
}

func (p *Publisher) Publish(ctx context.Context, routingKey string, body []byte) error {
	p.mu.Lock()
	defer p.mu.Unlock()

	return p.channel.PublishWithContext(ctx,
		"raw_events",    // exchange
		routingKey,      // routing key
		false,           // mandatory
		false,           // immediate
		amqp.Publishing{
			ContentType:  "application/json",
			Body:         body,
			DeliveryMode: amqp.Persistent,
			Timestamp:    time.Now(),
		})
}

func (p *Publisher) PublishHeartbeat(ctx context.Context, scraperName string) error {
	p.mu.Lock()
	defer p.mu.Unlock()

	body := fmt.Sprintf(`{"scraper":"%s","timestamp":"%s"}`, scraperName, time.Now().Format(time.RFC3339))
	return p.channel.PublishWithContext(ctx,
		"scraper_heartbeats",
		"scraper."+scraperName,
		false, false,
		amqp.Publishing{
			ContentType: "application/json",
			Body:        []byte(body),
		})
}

func (p *Publisher) reconnectLoop() {
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	for range ticker.C {
		p.mu.Lock()
		if p.channel == nil || p.conn == nil || p.conn.IsClosed() {
			p.logger.Info("reconnecting to rabbitmq...")
			// Reconnection logic would go here
		}
		p.mu.Unlock()
	}
}

func (p *Publisher) Close() error {
	p.mu.Lock()
	defer p.mu.Unlock()
	if p.channel != nil {
		p.channel.Close()
	}
	if p.conn != nil {
		return p.conn.Close()
	}
	return nil
}

// ─── Token Bucket Rate Limiter ───

type TokenBucket struct {
	capacity   int
	tokens     int
	refillRate int           // tokens per window
	window     time.Duration
	mu         sync.Mutex
	cond       *sync.Cond
	lastRefill time.Time
}

func NewTokenBucket(capacity int, window time.Duration, burst int) *TokenBucket {
	tb := &TokenBucket{
		capacity:   capacity,
		tokens:     burst,
		refillRate: capacity,
		window:     window,
		lastRefill: time.Now(),
	}
	tb.cond = sync.NewCond(&tb.mu)
	go tb.refillLoop()
	return tb
}

func (tb *TokenBucket) refillLoop() {
	ticker := time.NewTicker(tb.window)
	defer ticker.Stop()

	for range ticker.C {
		tb.mu.Lock()
		tb.tokens = tb.capacity
		tb.lastRefill = time.Now()
		tb.cond.Broadcast()
		tb.mu.Unlock()
	}
}

func (tb *TokenBucket) Take(ctx context.Context) error {
	tb.mu.Lock()
	defer tb.mu.Unlock()

	for tb.tokens <= 0 {
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
			tb.cond.Wait()
		}
	}
	tb.tokens--
	return nil
}

// ─── Redis Client ───

func NewRedisClient(addr, password string, db int) *redis.Client {
	return redis.NewClient(&redis.Options{
		Addr:     addr,
		Password: password,
		DB:       db,
	})
}