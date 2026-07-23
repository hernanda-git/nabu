package scraper

import (
	"context"
	"encoding/json"
	"fmt"
	"math/big"
	"strings"
	"sync"
	"time"

	"github.com/ethereum/go-ethereum"
	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/ethclient"
	"go.uber.org/zap"
)

// ─── Blockchain Scraper ───

type BlockchainScraper struct {
	*BaseScraper
	clients       map[string]*ethclient.Client
	chains        []ChainConfig
	contractABIs  map[string]abi.ABI
	filters       map[string][]FilterConfig
	mu            sync.RWMutex
}

type ChainConfig struct {
	Name           string   `yaml:"name"`
	RPCEndpoints   []string `yaml:"rpc_endpoints"`
	ChainID        int64    `yaml:"chain_id"`
	NativeCurrency string   `yaml:"native_currency"`
	ExplorerAPI    string   `yaml:"explorer_api"`
	ExplorerKey    string   `yaml:"explorer_key"`
	Monitors       []MonitorConfig `yaml:"monitors"`
}

type MonitorConfig struct {
	Type      string   `yaml:"type"`        // "new_contracts", "token_events", "bridge_events"
	Chains    []string `yaml:"chains"`
	Addresses []string `yaml:"addresses"`
	Events    []string `yaml:"events"`
	ABIPaths  []string `yaml:"abi_paths"`
}

type FilterConfig struct {
	MinValue       string   `yaml:"min_value"`
	TokenAddresses []string `yaml:"token_addresses"`
	EventTypes     []string `yaml:"event_types"`
}

func NewBlockchainScraper(config ScraperConfig, logger *zap.Logger, publisher *Publisher) (*BlockchainScraper, error) {
	base := NewBaseScraper("blockchain", config, logger, publisher)

	chains := parseChainConfigs(config)
	clients := make(map[string]*ethclient.Client)

	for _, chain := range chains {
		for _, endpoint := range chain.RPCEndpoints {
			client, err := ethclient.Dial(endpoint)
			if err != nil {
				logger.Warn("failed to connect to RPC", zap.String("chain", chain.Name), zap.String("endpoint", endpoint), zap.Error(err))
				continue
			}
			clients[chain.Name] = client
			break // Use first working endpoint
		}
	}

	return &BlockchainScraper{
		BaseScraper:  base,
		clients:      clients,
		chains:       chains,
		contractABIs: make(map[string]abi.ABI),
		filters:      make(map[string][]FilterConfig),
	}, nil
}

func (b *BlockchainScraper) Start(ctx context.Context) error {
	b.logger.Info("starting blockchain scraper", zap.Int("chains", len(b.clients)))

	// Load ABIs
	if err := b.loadABIs(ctx); err != nil {
		return fmt.Errorf("load ABIs: %w", err)
	}

	// Start heartbeat
	go b.heartbeat(ctx)

	// Start monitors for each chain
	for _, chain := range b.chains {
		client, ok := b.clients[chain.Name]
		if !ok {
			b.logger.Warn("no client for chain", zap.String("chain", chain.Name))
			continue
		}

		for _, monitor := range chain.Monitors {
			b.wg.Add(1)
			go b.runMonitor(ctx, chain.Name, client, monitor)
		}
	}

	// Start new contract deployment monitor
	b.wg.Add(1)
	go b.monitorNewContracts(ctx)

	return nil
}

func (b *BlockchainScraper) Stop() error {
	close(b.stopChan)
	b.wg.Wait()
	for _, client := range b.clients {
		client.Close()
	}
	return nil
}

func (b *BlockchainScraper) loadABIs(ctx context.Context) error {
	// Load standard ERC20, ERC721, bridge ABIs
	abis := map[string]string{
		"erc20":     erc20ABI,
		"erc721":    erc721ABI,
		"layerzero": layerZeroABI,
		"ccip":      ccipABI,
	}
	
	for name, abiStr := range abis {
		parsed, err := abi.JSON(strings.NewReader(abiStr))
		if err != nil {
			b.logger.Warn("failed to parse ABI", zap.String("name", name), zap.Error(err))
			continue
		}
		b.contractABIs[name] = parsed
	}
	return nil
}

func (b *BlockchainScraper) runMonitor(ctx context.Context, chainName string, client *ethclient.Client, monitor MonitorConfig) {
	defer b.wg.Done()

	switch monitor.Type {
	case "token_events":
		b.monitorTokenEvents(ctx, chainName, client, monitor)
	case "bridge_events":
		b.monitorBridgeEvents(ctx, chainName, client, monitor)
	case "new_contracts":
		b.monitorNewContracts(ctx, chainName, client, monitor)
	}
}

func (b *BlockchainScraper) monitorTokenEvents(ctx context.Context, chainName string, client *ethclient.Client, monitor MonitorConfig) {
	query := ethereum.FilterQuery{
		Addresses: parseAddresses(monitor.Addresses),
		Topics:    [][]common.Hash{{transferTopic}},
	}

	logs := make(chan types.Log)
	sub, err := client.SubscribeFilterLogs(ctx, query, logs)
	if err != nil {
		b.logger.Error("failed to subscribe to token events", zap.Error(err))
		return
	}
	defer sub.Unsubscribe()

	for {
		select {
		case <-ctx.Done():
			return
		case <-b.stopChan:
			return
		case err := <-sub.Err():
			b.recordError(err)
			// Resubscribe
			time.Sleep(5 * time.Second)
			return
		case vLog := <-logs:
			b.processTokenEvent(ctx, chainName, vLog)
		}
	}
}

func (b *BlockchainScraper) processTokenEvent(ctx context.Context, chainName string, vLog types.Log) {
	if len(vLog.Topics) < 1 || vLog.Topics[0] != transferTopic {
		return
	}

	// Parse Transfer event
	var transferEvent struct {
		From  common.Address
		To    common.Address
		Value *big.Int
	}

	abi := b.contractABIs["erc20"]
	if err := abi.UnpackIntoInterface(&transferEvent, "Transfer", vLog.Data); err != nil {
		b.logger.Debug("unpack transfer failed", zap.Error(err))
		return
	}
	transferEvent.From = common.BytesToAddress(vLog.Topics[1].Bytes())
	transferEvent.To = common.BytesToAddress(vLog.Topics[2].Bytes())

	// Check if this is a significant transfer
	if transferEvent.Value.Cmp(big.NewInt(1e18)) < 0 { // < 1 token
		return
	}

	event := RawEvent{
		ID:          fmt.Sprintf("evt_bc_%s_%s_%d", chainName, vLog.TxHash.Hex(), vLog.Index),
		Source:      "blockchain",
		SourceID:    vLog.TxHash.Hex(),
		Type:        "token_transfer",
		CollectedAt: time.Now(),
		Raw:         mustMarshal(vLog),
		Metadata: map[string]interface{}{
			"chain":        chainName,
			"contract":     vLog.Address.Hex(),
			"from":         transferEvent.From.Hex(),
			"to":           transferEvent.To.Hex(),
			"value":        transferEvent.Value.String(),
			"block_number": vLog.BlockNumber,
			"tx_hash":      vLog.TxHash.Hex(),
		},
		Confidence: 0.85,
	}

	if err := b.publishEvent(ctx, event); err != nil {
		b.logger.Error("publish failed", zap.Error(err))
	} else {
		b.recordEvent()
	}
}

func (b *BlockchainScraper) monitorBridgeEvents(ctx context.Context, chainName string, client *ethclient.Client, monitor MonitorConfig) {
	// Monitor LayerZero, CCIP, Wormhole, etc.
	bridgeConfigs := map[string]BridgeConfig{
		"layerzero": {
			Endpoint: "0x...", // LayerZero endpoint per chain
			Events:   []string{"PacketSent", "PacketReceived"},
		},
		"ccip": {
			Router: "0x...",
			Events: []string{"CCIPSendRequested", "CCIPReceiveRequested"},
		},
	}

	for name, config := range bridgeConfigs {
		if !contains(monitor.Addresses, config.Endpoint) && len(monitor.Addresses) > 0 {
			continue
		}
		
		b.wg.Add(1)
		go b.monitorBridge(ctx, chainName, client, name, config)
	}
}

func (b *BlockchainScraper) monitorBridge(ctx context.Context, chainName string, client *ethclient.Client, name string, config BridgeConfig) {
	defer b.wg.Done()

	query := ethereum.FilterQuery{
		Addresses: []common.Address{common.HexToAddress(config.Endpoint)},
	}

	logs := make(chan types.Log)
	sub, err := client.SubscribeFilterLogs(ctx, query, logs)
	if err != nil {
		b.logger.Error("bridge subscribe failed", zap.String("bridge", name), zap.Error(err))
		return
	}
	defer sub.Unsubscribe()

	for {
		select {
		case <-ctx.Done():
			return
		case <-b.stopChan:
			return
		case err := <-sub.Err():
			b.recordError(err)
			time.Sleep(5 * time.Second)
			return
		case vLog := <-logs:
			b.processBridgeEvent(ctx, chainName, name, vLog)
		}
	}
}

func (b *BlockchainScraper) processBridgeEvent(ctx context.Context, chainName, bridgeName string, vLog types.Log) {
	event := RawEvent{
		ID:          fmt.Sprintf("evt_bridge_%s_%s_%d", bridgeName, chainName, vLog.Index),
		Source:      "blockchain",
		SourceID:    vLog.TxHash.Hex(),
		Type:        "bridge_event",
		CollectedAt: time.Now(),
		Raw:         mustMarshal(vLog),
		Metadata: map[string]interface{}{
			"chain":        chainName,
			"bridge":       bridgeName,
			"contract":     vLog.Address.Hex(),
			"block_number": vLog.BlockNumber,
			"tx_hash":      vLog.TxHash.Hex(),
		},
		Confidence: 0.9,
	}

	if err := b.publishEvent(ctx, event); err != nil {
		b.logger.Error("publish failed", zap.Error(err))
	} else {
		b.recordEvent()
	}
}

func (b *BlockchainScraper) monitorNewContracts(ctx context.Context) {
	defer b.wg.Done()

	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	seenContracts := make(map[string]bool)

	for {
		select {
		case <-ctx.Done():
			return
		case <-b.stopChan:
			return
		case <-ticker.C:
			for chainName, client := range b.clients {
				if err := b.checkNewContracts(ctx, chainName, client, seenContracts); err != nil {
					b.recordError(err)
				}
			}
		}
	}
}

func (b *BlockchainScraper) checkNewContracts(ctx context.Context, chainName string, client *ethclient.Client, seen map[string]bool) error {
	// Get latest block
	header, err := client.HeaderByNumber(ctx, nil)
	if err != nil {
		return err
	}

	// Check transactions in latest block for contract creations
	block, err := client.BlockByNumber(ctx, header.Number)
	if err != nil {
		return err
	}

	for _, tx := range block.Transactions() {
		if tx.To() == nil { // Contract creation
			receipt, err := client.TransactionReceipt(ctx, tx.Hash())
			if err != nil {
				continue
			}
			if receipt.ContractAddress != (common.Address{}) {
				contractKey := fmt.Sprintf("%s:%s", chainName, receipt.ContractAddress.Hex())
				if !seen[contractKey] {
					seen[contractKey] = true
					
					event := RawEvent{
						ID:          fmt.Sprintf("evt_contract_%s_%s", chainName, receipt.ContractAddress.Hex()),
						Source:      "blockchain",
						SourceID:    tx.Hash().Hex(),
						Type:        "contract_deployment",
						CollectedAt: time.Now(),
						Raw:         mustMarshal(receipt),
						Metadata: map[string]interface{}{
							"chain":             chainName,
							"contract_address":  receipt.ContractAddress.Hex(),
							"deployer":          getTxSender(tx, receipt),
							"tx_hash":           tx.Hash().Hex(),
							"block_number":      receipt.BlockNumber.Uint64(),
							"gas_used":          receipt.GasUsed,
						},
						Confidence: 0.95,
					}

					if err := b.publishEvent(ctx, event); err != nil {
						b.logger.Error("publish failed", zap.Error(err))
					} else {
						b.recordEvent()
					}
				}
			}
		}
	}
	return nil
}

// ─── Helpers ───

func parseChainConfigs(config ScraperConfig) []ChainConfig {
	var chains []ChainConfig
	// In production: parse from config.Monitors or separate chain config
	return chains
}

func parseAddresses(addrs []string) []common.Address {
	var res []common.Address
	for _, a := range addrs {
		res = append(res, common.HexToAddress(a))
	}
	return res
}

func contains(slice []string, item string) bool {
	for _, s := range slice {
		if s == item {
			return true
		}
	}
	return false
}

func mustMarshal(v interface{}) json.RawMessage {
	data, _ := json.Marshal(v)
	return data
}

func getTxSender(tx *types.Transaction, receipt *types.Receipt) string {
	signer := types.LatestSignerForChainID(tx.ChainId())
	from, err := signer.Sender(tx)
	if err != nil {
		return "unknown"
	}
	return from.Hex()
}

// ─── ABIs ───

const erc20ABI = `[
	{"anonymous":false,"inputs":[{"indexed":true,"name":"from","type":"address"},{"indexed":true,"name":"to","type":"address"},{"indexed":false,"name":"value","type":"uint256"}],"name":"Transfer","type":"event"},
	{"anonymous":false,"inputs":[{"indexed":true,"name":"owner","type":"address"},{"indexed":true,"name":"spender","type":"address"},{"indexed":false,"name":"value","type":"uint256"}],"name":"Approval","type":"event"},
	{"inputs":[{"name":"account","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"type":"function"},
	{"inputs":[{"name":"spender","type":"address"},{"name":"amount","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"type":"function"}
]`

const erc721ABI = `[
	{"anonymous":false,"inputs":[{"indexed":true,"name":"from","type":"address"},{"indexed":true,"name":"to","type":"address"},{"indexed":true,"name":"tokenId","type":"uint256"}],"name":"Transfer","type":"event"},
	{"anonymous":false,"inputs":[{"indexed":true,"name":"owner","type":"address"},{"indexed":true,"name":"approved","type":"address"},{"indexed":true,"name":"tokenId","type":"uint256"}],"name":"Approval","type":"event"}
]`

const layerZeroABI = `[
	{"anonymous":false,"inputs":[{"indexed":true,"name":"dstChainId","type":"uint16"},{"indexed":true,"name":"srcAddress","type":"bytes32"},{"indexed":false,"name":"payloadHash","type":"bytes32"}],"name":"PacketSent","type":"event"},
	{"anonymous":false,"inputs":[{"indexed":true,"name":"srcChainId","type":"uint16"},{"indexed":true,"name":"srcAddress","type":"bytes32"},{"indexed":false,"name":"payloadHash","type":"bytes32"}],"name":"PacketReceived","type":"event"}
]`

const ccipABI = `[
	{"anonymous":false,"inputs":[{"indexed":true,"name":"messageId","type":"bytes32"},{"indexed":false,"name":"sourceChainSelector","type":"uint64"},{"indexed":false,"name":"sender","type":"bytes"},{"indexed":false,"name":"data","type":"bytes"}],"name":"CCIPSendRequested","type":"event"}
]`

var transferTopic = common.HexToHash("0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef")

type BridgeConfig struct {
	Endpoint string
	Router   string
	Events   []string
}