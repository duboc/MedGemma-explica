#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

cleanup() {
  echo ""
  echo -e "${CYAN}Shutting down...${NC}"
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
  echo -e "${GREEN}Done.${NC}"
}
trap cleanup EXIT

# --- Backend setup ---
echo -e "${CYAN}Setting up backend...${NC}"
if [ ! -d "$BACKEND_DIR/.venv" ]; then
  python3 -m venv "$BACKEND_DIR/.venv"
fi
source "$BACKEND_DIR/.venv/bin/activate"
pip install -q -r "$BACKEND_DIR/requirements.txt"

echo -e "${GREEN}Starting backend on http://localhost:8080${NC}"
uvicorn main:app --reload --port 8080 --app-dir "$BACKEND_DIR" &
BACKEND_PID=$!

# --- Frontend setup ---
echo -e "${CYAN}Setting up frontend...${NC}"
cd "$FRONTEND_DIR"
if [ ! -d "node_modules" ]; then
  npm install
fi

echo -e "${GREEN}Starting frontend...${NC}"
npm run dev &
FRONTEND_PID=$!

echo ""
echo -e "${GREEN}==================================${NC}"
echo -e "${GREEN}  Backend:  http://localhost:8080${NC}"
echo -e "${GREEN}  Frontend: http://localhost:3000${NC}"
echo -e "${GREEN}==================================${NC}"
echo -e "${CYAN}Press Ctrl+C to stop both.${NC}"
echo ""

wait
