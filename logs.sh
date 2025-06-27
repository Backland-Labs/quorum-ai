#!/bin/bash

# Quorum AI Log Streaming Script
# Stream logs from running services

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

case "${1:-both}" in
    backend|be)
        print_status "Streaming backend logs (Ctrl+C to exit)..."
        if [ -f "backend.log" ]; then
            tail -f backend.log | sed "s/^/$(echo -e "${CYAN}[BACKEND]${NC}") /"
        else
            print_error "backend.log not found. Is the backend running?"
            exit 1
        fi
        ;;
    frontend|fe)
        print_status "Streaming frontend logs (Ctrl+C to exit)..."
        if [ -f "frontend.log" ]; then
            tail -f frontend.log | sed "s/^/$(echo -e "${GREEN}[FRONTEND]${NC}") /"
        else
            print_error "frontend.log not found. Is the frontend running?"
            exit 1
        fi
        ;;
    both|"")
        print_status "Streaming both backend and frontend logs (Ctrl+C to exit)..."
        if [ ! -f "backend.log" ] && [ ! -f "frontend.log" ]; then
            print_error "No log files found. Are the services running?"
            exit 1
        fi
        
        # Stream both logs with different colors and prefixes
        (
            if [ -f "backend.log" ]; then
                tail -f backend.log | sed "s/^/$(echo -e "${CYAN}[BACKEND]${NC}") /" &
            fi
            if [ -f "frontend.log" ]; then
                tail -f frontend.log | sed "s/^/$(echo -e "${GREEN}[FRONTEND]${NC}") /" &
            fi
            wait
        )
        ;;
    --help|-h)
        echo "Usage: $0 [backend|frontend|both]"
        echo ""
        echo "Stream logs from running Quorum AI services"
        echo ""
        echo "Options:"
        echo "  backend, be   Stream only backend logs"
        echo "  frontend, fe  Stream only frontend logs" 
        echo "  both          Stream both logs (default)"
        echo "  --help, -h    Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0              # Stream both logs"
        echo "  $0 backend      # Stream only backend"
        echo "  $0 fe           # Stream only frontend (short form)"
        ;;
    *)
        print_error "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac