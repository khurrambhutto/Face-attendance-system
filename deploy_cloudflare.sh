#!/bin/bash
#
# Deploy Enrollment App with Cloudflare Tunnel
# Students can access via HTTPS URL from anywhere
# No account required!
#

echo "============================================================"
echo "       FACE ENROLLMENT - CLOUDFLARE TUNNEL"
echo "============================================================"
echo ""

# Check if cloudflared is installed
if ! command -v cloudflared &> /dev/null; then
    echo "❌ cloudflared not found!"
    echo ""
    echo "Install cloudflared first:"
    echo ""
    echo "  # For Linux (Debian/Ubuntu)"
    echo "  wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb"
    echo "  sudo dpkg -i cloudflared-linux-amd64.deb"
    echo ""
    echo "  # For other systems:"
    echo "  # Visit: https://github.com/cloudflare/cloudflared/releases"
    echo ""
    exit 1
fi

# Check if Streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo "❌ Streamlit not found!"
    echo "   Install: pip install streamlit"
    exit 1
fi

echo "✓ cloudflared found"
echo "✓ Streamlit found"
echo ""

# Kill any existing processes on port 8501
echo "🧹 Cleaning up port 8501..."
fuser -k 8501/tcp 2>/dev/null || true
sleep 2

# Start Streamlit in background
echo ""
echo "🚀 Starting Streamlit enrollment app..."
echo "   Port: 8501"
echo "   Headless mode: ON"
echo ""

streamlit run enrollment_app.py \
    --server.port 8501 \
    --server.headless true \
    --browser.gatherUsageStats false \
    > /dev/null 2>&1 &

STREAMLIT_PID=$!
echo "✓ Streamlit started (PID: $STREAMLIT_PID)"
echo ""

# Wait for Streamlit to start
echo "⏳ Waiting for Streamlit to start..."
sleep 5

# Check if Streamlit is running
if ! ps -p $STREAMLIT_PID > /dev/null; then
    echo "❌ Streamlit failed to start"
    exit 1
fi

echo "✓ Streamlit is running"
echo ""

# Start Cloudflare tunnel
echo "🌐 Starting Cloudflare tunnel..."
echo ""
echo "📱 Share this URL with students:"
echo ""

cloudflared tunnel --url http://localhost:8501

echo ""
echo "============================================================"
echo "TUNNEL STOPPED"
echo "============================================================"
echo ""
echo "Streamlit is still running (PID: $STREAMLIT_PID)"
echo "To stop it:"
echo "  kill $STREAMLIT_PID"
echo ""

# Cleanup
kill $STREAMLIT_PID 2>/dev/null
