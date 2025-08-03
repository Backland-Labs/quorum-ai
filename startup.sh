#!/bin/bash

# Quorum AI Startup Script
# This script launches both the backend and frontend services
# Usage: ./startup.sh [--logs|--background]

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if port is available
port_available() {
    ! lsof -i :$1 >/dev/null 2>&1
}

# Function to load environment variables from .env file
load_env() {
    if [ -f ".env" ]; then
        print_status "Loading environment variables from .env file..."
        # Export variables from .env file, ignoring comments and empty lines
        export $(grep -v '^#' .env | grep -v '^$' | xargs)
        print_success "Environment variables loaded"
    else
        print_warning ".env file not found. Using system environment variables only."
    fi
}

# Function to cleanup background processes on script exit
cleanup() {
    print_status "Shutting down services..."
    if [[ -n $BACKEND_PID ]]; then
        kill $BACKEND_PID 2>/dev/null || true
        print_status "Backend service stopped"
    fi
    if [[ -n $FRONTEND_PID ]]; then
        kill $FRONTEND_PID 2>/dev/null || true
        print_status "Frontend service stopped"
    fi
    exit 0
}

# Set up signal handlers for graceful shutdown
trap cleanup SIGINT SIGTERM

# Parse command line arguments
STREAM_LOGS=false
BACKGROUND_MODE=true

case "${1:-}" in
    --logs)
        STREAM_LOGS=true
        BACKGROUND_MODE=false
        ;;
    --background)
        STREAM_LOGS=false
        BACKGROUND_MODE=true
        ;;
    --help|-h)
        echo "Usage: $0 [--logs|--background]"
        echo ""
        echo "Options:"
        echo "  --logs        Stream logs to terminal (services run in foreground)"
        echo "  --background  Run services in background with log files (default)"
        echo "  --help, -h    Show this help message"
        exit 0
        ;;
    "")
        # Default behavior
        ;;
    *)
        print_error "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac

print_status "Starting Quorum AI services..."

# Load environment variables
load_env

# Check required commands
if ! command_exists uv; then
    print_error "uv is not installed. Please install it first: pip install uv"
    exit 1
fi

if ! command_exists npm; then
    print_error "npm is not installed. Please install Node.js and npm"
    exit 1
fi

# Check if ports are available
BACKEND_PORT=${HEALTH_CHECK_PORT:-8716}
print_status "Checking if backend port $BACKEND_PORT is available..."
if ! port_available $BACKEND_PORT; then
    print_error "Port $BACKEND_PORT is already in use. Please stop the service using this port."
    # Show what's using the port
    print_warning "Process using port $BACKEND_PORT:"
    lsof -i :$BACKEND_PORT || true
    exit 1
fi
print_success "Backend port $BACKEND_PORT is available"

print_status "Checking if frontend port 5173 is available..."
if ! port_available 5173; then
    print_error "Port 5173 is already in use. Please stop the service using this port."
    # Show what's using the port
    print_warning "Process using port 5173:"
    lsof -i :5173 || true
    exit 1
fi
print_success "Frontend port 5173 is available"

# Start Backend
print_status "Starting backend server on port $BACKEND_PORT..."
cd backend
if [ ! -f "main.py" ]; then
    print_error "Backend main.py not found. Make sure you're in the correct directory."
    exit 1
fi

if [ "$BACKGROUND_MODE" = true ]; then
    # Start backend in background
    print_status "Running: uv run --active main.py"
    uv run --active main.py > ../backend.log 2>&1 &
    BACKEND_PID=$!
    cd ..

    # Wait a moment for backend to start
    print_status "Waiting for backend to start..."
    sleep 3

    # Check if backend started successfully
    if ! ps -p $BACKEND_PID > /dev/null; then
        print_error "Backend failed to start. Check backend.log for details."
        print_warning "Last 20 lines of backend.log:"
        tail -n 20 backend.log 2>/dev/null || print_error "Could not read backend.log"
        exit 1
    fi

    # Check if backend is actually listening on the port
    if ! lsof -i :$BACKEND_PORT | grep -q LISTEN; then
        print_error "Backend process is running but not listening on port $BACKEND_PORT"
        print_warning "Last 20 lines of backend.log:"
        tail -n 20 backend.log 2>/dev/null || print_error "Could not read backend.log"
        cleanup
        exit 1
    fi

    print_success "Backend started successfully (PID: $BACKEND_PID) on port $BACKEND_PORT"
else
    # Start backend in foreground for log streaming
    print_status "Starting backend in foreground mode..."
    cd ..
fi

# Start Frontend
print_status "Starting frontend server on port 5173..."
cd frontend

if [ ! -f "package.json" ]; then
    print_error "Frontend package.json not found. Make sure you're in the correct directory."
    exit 1
fi

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    print_warning "node_modules not found. Installing dependencies..."
    npm install
fi

if [ "$BACKGROUND_MODE" = true ]; then
    # Generate API client from backend
    print_status "Generating API client from backend..."
    npm run generate-api > ../frontend.log 2>&1 || print_warning "API client generation failed. Backend might not be fully ready yet."

    # Start frontend in background
    npm run dev >> ../frontend.log 2>&1 &
    FRONTEND_PID=$!
    cd ..

    # Wait a moment for frontend to start
    sleep 3

    # Check if frontend started successfully
    if ! ps -p $FRONTEND_PID > /dev/null; then
        print_error "Frontend failed to start. Check frontend.log for details."
        print_warning "Last 20 lines of frontend.log:"
        tail -n 20 frontend.log 2>/dev/null || print_error "Could not read frontend.log"
        cleanup
        exit 1
    fi

    print_success "Frontend started successfully (PID: $FRONTEND_PID)"
else
    # In foreground mode, start both services with log streaming
    print_status "Generating API client from backend..."
    npm run generate-api || print_warning "API client generation failed. Will continue anyway."

    cd ..
    print_status "Starting services in foreground with streaming logs..."
    print_status "Press Ctrl+C to stop all services"
    echo ""

    # Use a process substitution to stream logs with prefixes
    (cd backend && uv run --active main.py 2>&1 | sed 's/^/[BACKEND] /') &
    BACKEND_PID=$!

    sleep 2  # Give backend a moment to start

    (cd frontend && npm run dev 2>&1 | sed 's/^/[FRONTEND] /') &
    FRONTEND_PID=$!

    # Wait for both processes
    wait $BACKEND_PID $FRONTEND_PID
    exit 0
fi

# Display service information
echo ""
print_success "🚀 Quorum AI services are running!"
echo ""
echo -e "${BLUE}Services:${NC}"
echo -e "  🔧 Backend API:    ${GREEN}http://localhost:${BACKEND_PORT}${NC}"
echo -e "  📚 API Docs:       ${GREEN}http://localhost:${BACKEND_PORT}/docs${NC}"
echo -e "  🌐 Frontend App:   ${GREEN}http://localhost:5173${NC}"
echo ""
echo -e "${BLUE}Process IDs:${NC}"
echo -e "  Backend PID:  ${BACKEND_PID}"
echo -e "  Frontend PID: ${FRONTEND_PID}"
echo ""
echo -e "${BLUE}Logs:${NC}"
echo -e "  Backend:  tail -f backend.log"
echo -e "  Frontend: tail -f frontend.log"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"

# Only run the monitoring loop in background mode
if [ "$BACKGROUND_MODE" = true ]; then
    # Wait for user interrupt
    while true; do
        sleep 1
        # Check if processes are still running
        if ! ps -p $BACKEND_PID > /dev/null; then
            print_error "Backend process died unexpectedly"
            cleanup
            exit 1
        fi
        if ! ps -p $FRONTEND_PID > /dev/null; then
            print_error "Frontend process died unexpectedly"
            cleanup
            exit 1
        fi
    done
fi
