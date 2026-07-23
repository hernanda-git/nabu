# 𒀭 Nabu Makefile — Orchestration for the Eternal Oracle

.PHONY: daemon swarm cron health status logs clean

# ─── Daemon (Eternal Loop) ───────────────────────────────────
daemon:
	@echo "𒀭 Starting Nabu daemon..."
	@python runtime/nabu_daemon.py

daemon-bg:
	@echo "𒀭 Starting Nabu daemon in background..."
	@python runtime/nabu_daemon.py &

# ─── Swarm Agents ──────────────────────────────────────────────
swarm:
	@echo "𒀭 Starting Nabu swarm (all agents)..."
	@python runtime/agents/nabu_swarm.py --all

swarm-scout:
	@python runtime/agents/nabu_swarm.py --agent scout

swarm-analysis:
	@python runtime/agents/nabu_swarm.py --agent analysis

swarm-scam:
	@python runtime/agents/nabu_swarm.py --agent scam

swarm-gas:
	@python runtime/agents/nabu_swarm.py --agent gas

swarm-historical:
	@python runtime/agents/nabu_swarm.py --agent historical

swarm-authority:
	@python runtime/agents/nabu_swarm.py --agent authority

swarm-correction:
	@python runtime/agents/nabu_swarm.py --agent correction

swarm-broadcast:
	@python runtime/agents/nabu_swarm.py --agent broadcast

# ─── Cron Jobs ───────────────────────────────────────────────
cron-source-watch:
	@python runtime/cron/nabu_cron.py source_watch_5m

cron-deep-analysis:
	@python runtime/cron/nabu_cron.py deep_analysis_15m

cron-self-correct:
	@python runtime/cron/nabu_cron.py self_correct_hourly

cron-market-regime:
	@python runtime/cron/nabu_cron.py market_regime_6h

cron-source-authority:
	@python runtime/cron/nabu_cron.py source_authority_12h

cron-historical:
	@python runtime/cron/nabu_cron.py historical_patterns_daily

cron-gas-costs:
	@python runtime/cron/nabu_cron.py gas_costs_daily

cron-health:
	@python runtime/cron/nabu_cron.py health_check_weekly

cron-list:
	@python runtime/cron/nabu_cron.py list

# ─── Status & Monitoring ─────────────────────────────────────
status:
	@echo "𒀭 Nabu Status:"
	@echo "  Daemon: $$(pgrep -f nabu_daemon.py | head -1 || echo 'not running')"
	@echo "  Swarm agents: $$(pgrep -f nabu_swarm.py | wc -l)"
	@echo "  State: $$(cat runtime/nabu_state.json 2>/dev/null | python -m json.tool 2>/dev/null || echo 'no state')"

health:
	@echo "𒀭 Nabu Health Check:"
	@python runtime/cron/nabu_cron.py health_check_weekly

logs:
	@tail -f runtime/logs/nabu.log

logs-swarm:
	@tail -f runtime/logs/nabu_swarm.log

logs-cron:
	@tail -f runtime/logs/nabu_cron.log

# ─── Maintenance ─────────────────────────────────────────────
clean:
	@rm -f runtime/nabu_state.json runtime/swarm_state.json
	@rm -f runtime/logs/*.log
	@echo "𒀭 Nabu state cleaned"

restart: clean daemon-bg
	@echo "𒀭 Nabu restarted"

# ─── Full Stack ──────────────────────────────────────────────
start: daemon-bg
	@echo "𒀭 Nabu daemon started"
	@sleep 2
	@echo "𒀭 Starting swarm agents..."
	@python runtime/agents/nabu_swarm.py --all &
	@echo "𒀭 Nabu is now alive — daemon + swarm running"

stop:
	@echo "𒀭 Stopping Nabu..."
	@pkill -f nabu_daemon.py || true
	@pkill -f nabu_swarm.py || true
	@echo "𒀭 Nabu stopped"
