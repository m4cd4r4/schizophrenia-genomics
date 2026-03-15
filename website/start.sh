#!/usr/bin/env bash
# Start both API and dashboard in parallel

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "Starting FastAPI backend on port 8001..."
cd "$ROOT" && PYTHONPATH="$ROOT" uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload &
API_PID=$!

echo "Starting Next.js dashboard on port 3000..."
cd "$ROOT/dashboard" && npm run dev &
DASH_PID=$!

echo ""
echo "  API:       http://localhost:8001"
echo "  Dashboard: http://localhost:3000"
echo "  API docs:  http://localhost:8001/docs"
echo ""
echo "Press Ctrl+C to stop both services."

trap "kill $API_PID $DASH_PID 2>/dev/null; exit 0" INT TERM
wait
