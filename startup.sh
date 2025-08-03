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
        print_status "Stopping backend service (PID: $BACKEND_PID)..."
        kill -TERM $BACKEND_PID 2>/dev/null || true
        # Wait a bit for graceful shutdown
        sleep 2
        # Force kill if still running
        if ps -p $BACKEND_PID > /dev/null 2>&1; then
            print_status "Force killing backend service..."
            kill -KILL $BACKEND_PID 2>/dev/null || true
        fi
        print_status "Backend service stopped"
    fi
    if [[ -n $FRONTEND_PID ]]; then
        print_status "Stopping frontend service (PID: $FRONTEND_PID)..."
        kill -TERM $FRONTEND_PID 2>/dev/null || true
        # Wait a bit for graceful shutdown
        sleep 2
        # Force kill if still running
        if ps -p $FRONTEND_PID > /dev/null 2>&1; then
            print_status "Force killing frontend service..."
            kill -KILL $FRONTEND_PID 2>/dev/null || true
        fi
        print_status "Frontend service stopped"
    fi
    exit 0
}

# Set up signal handlers for graceful shutdown
trap cleanup SIGINT SIGTERM

# Parse command line arguments
STREAM_LOGS=false
BACKGROUND_MODE=true
FORCE_KILL=true

for arg in "$@"; do
    case "$arg" in
        --logs)
            STREAM_LOGS=true
            BACKGROUND_MODE=false
            ;;
        --background)
            STREAM_LOGS=false
            BACKGROUND_MODE=true
            ;;
        --no-kill)
            FORCE_KILL=false
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --logs        Stream logs to terminal (services run in foreground)"
            echo "  --background  Run services in background with log files (default)"
            echo "  --no-kill     Don't kill existing processes on ports (exit if ports are in use)"
            echo "  --help, -h    Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                    # Run in background mode, kill existing processes"
            echo "  $0 --logs             # Stream logs to terminal"
            echo "  $0 --no-kill          # Exit if ports are already in use"
            echo "  $0 --logs --no-kill   # Stream logs, don't kill existing processes"
            exit 0
            ;;
        *)
            print_error "Unknown option: $arg"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

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

# Function to kill processes on a specific port
kill_port_process() {
    local port=$1
    local pids=$(lsof -ti :$port 2>/dev/null)
    
    if [ -n "$pids" ]; then
        print_warning "Killing processes on port $port..."
        for pid in $pids; do
            local process_info=$(ps -p $pid -o comm= 2>/dev/null || echo "unknown")
            print_status "  Killing process $pid ($process_info)"
            kill -9 $pid 2>/dev/null || true
        done
        sleep 1  # Give processes time to die
        return 0
    fi
    return 1
}

# Check and clean up ports
BACKEND_PORT=${HEALTH_CHECK_PORT:-8716}
print_status "Checking backend port $BACKEND_PORT..."
if ! port_available $BACKEND_PORT; then
    if [ "$FORCE_KILL" = true ]; then
        print_warning "Port $BACKEND_PORT is in use. Attempting to free it..."
        # Show what's using the port
        print_status "Process using port $BACKEND_PORT:"
        lsof -i :$BACKEND_PORT 2>/dev/null || true
        
        # Kill the process
        if kill_port_process $BACKEND_PORT; then
            print_success "Port $BACKEND_PORT has been freed"
        else
            print_error "Failed to free port $BACKEND_PORT"
            exit 1
        fi
    else
        print_error "Port $BACKEND_PORT is already in use. Please stop the service using this port."
        print_warning "Process using port $BACKEND_PORT:"
        lsof -i :$BACKEND_PORT 2>/dev/null || true
        print_status "Use --help to see options for killing existing processes"
        exit 1
    fi
else
    print_success "Backend port $BACKEND_PORT is available"
fi

print_status "Checking frontend port 5173..."
if ! port_available 5173; then
    if [ "$FORCE_KILL" = true ]; then
        print_warning "Port 5173 is in use. Attempting to free it..."
        # Show what's using the port
        print_status "Process using port 5173:"
        lsof -i :5173 2>/dev/null || true
        
        # Kill the process
        if kill_port_process 5173; then
            print_success "Port 5173 has been freed"
        else
            print_error "Failed to free port 5173"
            exit 1
        fi
    else
        print_error "Port 5173 is already in use. Please stop the service using this port."
        print_warning "Process using port 5173:"
        lsof -i :5173 2>/dev/null || true
        print_status "Use --help to see options for killing existing processes"
        exit 1
    fi
else
    print_success "Frontend port 5173 is available"
fi

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

    # Stream Pearl log.txt file if it exists, create it if it doesn't
    PEARL_LOG_FILE="backend/log.txt"
    if [ ! -f "$PEARL_LOG_FILE" ]; then
        print_status "Creating Pearl log file: $PEARL_LOG_FILE"
        mkdir -p "$(dirname "$PEARL_LOG_FILE")"
        touch "$PEARL_LOG_FILE"
    fi
    
    # Stream the Pearl log file with prefix
    tail -f "$PEARL_LOG_FILE" 2>/dev/null | sed 's/^/[PEARL] /' &
    PEARL_LOG_PID=$!

    # Function to cleanup all processes including Pearl log tail
    cleanup_with_pearl() {
        print_status "Shutting down all services and log streams..."
        if [[ -n $BACKEND_PID ]]; then
            print_status "Stopping backend service (PID: $BACKEND_PID)..."
            kill -TERM $BACKEND_PID 2>/dev/null || true
            # Wait a bit for graceful shutdown
            sleep 2
            # Force kill if still running
            if ps -p $BACKEND_PID > /dev/null 2>&1; then
                print_status "Force killing backend service..."
                kill -KILL $BACKEND_PID 2>/dev/null || true
            fi
        fi
        if [[ -n $FRONTEND_PID ]]; then
            print_status "Stopping frontend service (PID: $FRONTEND_PID)..."
            kill -TERM $FRONTEND_PID 2>/dev/null || true
            # Wait a bit for graceful shutdown
            sleep 2
            # Force kill if still running
            if ps -p $FRONTEND_PID > /dev/null 2>&1; then
                print_status "Force killing frontend service..."
                kill -KILL $FRONTEND_PID 2>/dev/null || true
            fi
        fi
        if [[ -n $PEARL_LOG_PID ]]; then
            kill -TERM $PEARL_LOG_PID 2>/dev/null || true
        fi
        print_status "All services stopped"
        exit 0
    }

    # Override the cleanup function for foreground mode
    trap cleanup_with_pearl SIGINT SIGTERM

    # Wait for both main processes (Pearl log will continue until killed)
    wait $BACKEND_PID $FRONTEND_PID
    cleanup_with_pearl
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
