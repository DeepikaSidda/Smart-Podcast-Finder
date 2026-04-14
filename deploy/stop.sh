#!/bin/bash
echo "Stopping all services..."
pkill -f "temporal server" 2>/dev/null || true
pkill -f "worker.py" 2>/dev/null || true
pkill -f "uvicorn" 2>/dev/null || true
echo "All services stopped."
