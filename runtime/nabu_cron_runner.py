#!/usr/bin/env python3
"""
𒀭 NABU — Sequential Cron Runner
Runs all 6 cron jobs sequentially in a loop with health/completion monitoring.
"""

import asyncio
import json
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

RUNTIME_DIR = Path(__file__).parent.parent
LOG_DIR = RUNTIME_DIR / "runtime" / "logs"
LOG_DIR.mkdir(exist_ok=True)

import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [NABU-CRON-RUNNER] %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "nabu_cron_runner.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("nabu_cron_runner")

# ─── Cron Job Definitions ───
CRON_JOBS = [
    ("nabu-source-watch", "source_watch_5m"),
    ("nabu-deep-analysis", "deep_analysis_15m"),
    ("nabu-self-correction", "self_correct_hourly"),
    ("nabu-market-regime", "market_regime_6h"),
    ("nabu-historical-patterns", "historical_patterns_daily"),
    ("nabu-health-check", "health_check_weekly"),
]

class CronRunner:
    def __init__(self):
        self.running = True
        self.cycle = 0
        self.job_results = {}
        self.health_status = "healthy"
        self.completion_status = {}
        self.correction_needed = False
        
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)
    
    def _handle_signal(self, signum, frame):
        log.info(f"𒀭 Received signal {signum} — stopping gracefully")
        self.running = False
    
    async def run_job(self, job_name: str, func_name: str) -> dict:
        """Run a single cron job."""
        log.info(f"🚀 Starting job: {job_name}")
        start = time.time()
        
        try:
            # Import and run the cron function
            sys.path.insert(0, str(RUNTIME_DIR / "runtime" / "cron"))
            from nabu_cron import (
                watch_sources, deep_analysis, self_correct,
                update_market_regime, rebuild_historical_patterns,
                weekly_health_check
            )
            
            func_map = {
                "source_watch_5m": watch_sources,
                "deep_analysis_15m": deep_analysis,
                "self_correct_hourly": self_correct,
                "market_regime_6h": update_market_regime,
                "historical_patterns_daily": rebuild_historical_patterns,
                "health_check_weekly": weekly_health_check,
            }
            
            func = func_map[func_name]
            await func()
            
            duration = time.time() - start
            result = {
                "job": job_name,
                "status": "completed",
                "duration_seconds": round(duration, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            log.info(f"✅ Job {job_name} completed in {duration:.2f}s")
            return result
            
        except Exception as e:
            duration = time.time() - start
            result = {
                "job": job_name,
                "status": "failed",
                "error": str(e),
                "duration_seconds": round(duration, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            log.error(f"❌ Job {job_name} failed: {e}")
            return result
    
    def check_health(self, results: dict) -> str:
        """Check overall health from job results."""
        failed = [r for r in results.values() if r.get("status") == "failed"]
        if failed:
            return "degraded"
        return "healthy"
    
    def check_completion(self, results: dict) -> bool:
        """Check if all jobs completed successfully."""
        return all(r.get("status") == "completed" for r in results.values())
    
    def check_correction_needed(self, results: dict) -> bool:
        """Check if self-correction or retry needed."""
        failed = [r for r in results.values() if r.get("status") == "failed"]
        return len(failed) > 0
    
    async def run_cycle(self):
        """Run one complete cycle of all 6 jobs."""
        self.cycle += 1
        log.info(f"𒀭 === CYCLE {self.cycle} START ===")
        
        cycle_start = time.time()
        cycle_results = {}
        
        # Run all 6 jobs sequentially
        for job_name, func_name in CRON_JOBS:
            if not self.running:
                break
            result = await self.run_job(job_name, func_name)
            cycle_results[job_name] = result
            self.job_results[job_name] = result
            
            # Brief pause between jobs (0.5s)
            await asyncio.sleep(0.5)
        
        # Post-cycle checks
        self.health_status = self.check_health(cycle_results)
        all_completed = self.check_completion(cycle_results)
        self.correction_needed = self.check_correction_needed(cycle_results)
        
        cycle_duration = time.time() - cycle_start
        
        # Log cycle summary
        completed = sum(1 for r in cycle_results.values() if r.get("status") == "completed")
        failed = sum(1 for r in cycle_results.values() if r.get("status") == "failed")
        
        log.info(f"𒀭 === CYCLE {self.cycle} COMPLETE ===")
        log.info(f"  Duration: {cycle_duration:.2f}s | Completed: {completed}/6 | Failed: {failed}/6")
        log.info(f"  Health: {self.health_status} | All Complete: {all_completed} | Correction Needed: {self.correction_needed}")
        
        # Save cycle state
        self.save_state(cycle_results)
        
        return all_completed
    
    def save_state(self, results: dict):
        """Save runner state to file."""
        state_file = RUNTIME_DIR / "runtime" / "cron_runner_state.json"
        state = {
            "cycle": self.cycle,
            "health_status": self.health_status,
            "correction_needed": self.correction_needed,
            "last_cycle_results": results,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)
    
    async def run_continuous(self):
        """Run cycles continuously until stopped or correction needed."""
        log.info("𒀭 Nabu Cron Runner starting continuous execution")
        
        while self.running:
            all_completed = await self.run_cycle()
            
            # Check stop conditions
            if not self.running:
                log.info("𒀭 Stop signal received")
                break
            
            if self.correction_needed:
                log.warning("𒀭 Correction needed — stopping for intervention")
                break
            
            if not all_completed:
                log.warning("𒀭 Not all jobs completed — stopping for review")
                break
            
            # Small delay before next cycle
            log.info("𒀭 Cycle complete — pausing 2s before next cycle")
            await asyncio.sleep(2)
        
        log.info("𒀭 Nabu Cron Runner stopped")
        self.save_final_state()
    
    def save_final_state(self):
        """Save final state."""
        state_file = RUNTIME_DIR / "runtime" / "cron_runner_final.json"
        state = {
            "final_cycle": self.cycle,
            "health_status": self.health_status,
            "correction_needed": self.correction_needed,
            "job_results": self.job_results,
            "stopped_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)
        log.info(f"𒀭 Final state saved to {state_file}")


async def main():
    runner = CronRunner()
    await runner.run_continuous()

if __name__ == "__main__":
    asyncio.run(main())