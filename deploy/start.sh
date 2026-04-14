#!/bin/bash
set -e

cd /home/ec2-user/Smart-Podcast-Finder
source .venv/bin/activate
export PATH="$HOME/.temporalio/bin:$PATH"

echo "=== Starting Smart Podcast Finder ==="

# Start Temporal server in background
echo "Starting Temporal server..."
nohup temporal server start-dev --ip 0.0.0.0 > /tmp/temporal.log 2>&1 &
sleep 3

# Start worker in background
echo "Starting worker..."
nohup python worker.py > /tmp/worker.log 2>&1 &
sleep 2

# Start API server (port 80 for public access)
echo "Starting API server on port 80..."
sudo .venv/bin/python -c "
import uvicorn
uvicorn.run('app.main:app', host='0.0.0.0', port=80)
" > /tmp/api.log 2>&1 &

echo ""
echo "=== All services started! ==="
echo "Logs:"
echo "  Temporal: /tmp/temporal.log"
echo "  Worker:   /tmp/worker.log"
echo "  API:      /tmp/api.log"
echo ""
echo "App is running on http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)"
