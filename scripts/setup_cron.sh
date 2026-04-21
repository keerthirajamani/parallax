#!/bin/bash
# Run once on EC2 to install the crontab
# Usage: bash scripts/setup_cron.sh

crontab -l 2>/dev/null > /tmp/current_cron

cat >> /tmp/current_cron << 'EOF'
# ── Parallax Signal Crons ─────────────────────────────────────────────────────

# IST schedules (NSE + token refresh)
CRON_TZ=Asia/Kolkata

# NSE daily signals — Mon-Fri at 15:26 IST (NSE market close)
26 15 * * 1-5 docker exec parallax python scripts/run.py signals '{"unit":"days","interval":1,"entity":"EQUITY"}' >> /var/log/parallax/nse_daily.log 2>&1

# NSE weekly signals — Friday at 15:26 IST
26 15 * * 5   docker exec parallax python scripts/run.py signals '{"unit":"weeks","interval":1,"entity":"EQUITY"}' >> /var/log/parallax/nse_weekly.log 2>&1

# Dhan token refresh — every day at 08:45 and 20:45 IST
45 8,20 * * * docker exec parallax python scripts/run.py token_refresh >> /var/log/parallax/token_refresh.log 2>&1

# New York schedules (NYSE — DST handled automatically)
CRON_TZ=America/New_York

# NYSE daily signals — Mon-Fri at 15:54 NY time
54 15 * * 1-5 docker exec parallax python scripts/run.py signals '{"unit":"days","interval":1,"entity":"US_EQUITY"}' >> /var/log/parallax/nyse_daily.log 2>&1

# NYSE weekly signals — Friday at 15:54 NY time
54 15 * * 5   docker exec parallax python scripts/run.py signals '{"unit":"weeks","interval":1,"entity":"US_EQUITY"}' >> /var/log/parallax/nyse_weekly.log 2>&1

EOF

crontab /tmp/current_cron
rm /tmp/current_cron

# Create log directory
sudo mkdir -p /var/log/parallax
sudo chown ec2-user:ec2-user /var/log/parallax

echo "Crontab installed:"
crontab -l
