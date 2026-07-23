#!/usr/bin/env python3
"""
𒀭 NABU — In-Session Sequential Loop
Runs all 6 jobs sequentially in a continuous loop within this session.
"""

import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

RUNTIME_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(RUNTIME_DIR / "runtime" / "cron"))

from nabu_cron import (
    watch_sources, deep_analysis, self_correct,
    update_market_regime, rebuild_historical_patterns,
    weekly_health_check
)

CRON_JOBS = [
    ("nabu-source-watch", "source_watch_5m", watch_sources),
    ("nabu-deep-analysis", "deep_analysis_15m", deep_analysis),
    ("nabu-self-correction", "self_correct_hourly", self_correct),
    ("nabu-market-regime", "market_regime_6h", update_market_regime),
    ("nabu-historical-patterns", "historical_patterns_daily", rebuild_historical_patterns),
    ("nabu-health-check", "health_check_weekly", weekly_health_check),
]

async def run_loop():
    """Run all 6 jobs sequentially in an infinite loop."""
    cycle = 0
    
    print("𒀭 Nabu In-Session Loop Started")
    print("=" * 60)
    
    while True:
        cycle += 1
        print(f"\n𒀭 === CYCLE {cycle} START ===")
        cycle_start = time.time()
        
        all_completed = True
        
        for job_name, func_name, func in CRON_JOBS:
            print(f"🚀 Starting job: {job_name}")
            start = time.time()
            
            try:
                await func()
                duration = time.time() - start
                print(f"✅ Job {job_name} completed in {duration:.2f}s")
            except Exception as e:
                duration = time.time() - start
                print(f"❌ Job {job_name} failed: {e}")
                all_completed = False
            
            # Brief pause between jobs
            await asyncio.sleep(0.5)
        
        cycle_duration = time.time() - cycle_start
        
        print(f"𒀭 === CYCLE {cycle} COMPLETE ===")
        print(f"  Duration: {cycle_duration:.2f}s | All Complete: {all_completed}")
        
        if not all_completed:
            print("⚠️  Not all jobs completed — stopping loop")
            break
        
        # Pause 2 seconds before next cycle
        print("𒀭 Pausing 2s before next cycle...")
        await asyncio.sleep(2)

if __name__ == "__main__":
    try:
        asyncio.run(run_loop())
    except KeyboardInterrupt:
        print("\n𒀭 Loop stopped by user")