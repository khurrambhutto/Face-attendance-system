#!/bin/bash
#
# Deploy Enrollment App with ngrok Tunnel
# Students can access via HTTPS URL from anywhere
#

echo "============================================================"
echo "       FACE ENROLLMENT - NGROK DEPLOYMENT"
echo "============================================================"
echo ""

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok not found!"
    echo ""
    echo "Install ngrok first:"
    echo "  1. Download: https://ngrok.com/download"
    echo "  2. Extract and move to /usr/local/bin"
    echo "  3. Or: sudo apt install ngrok (on some systems)"
    echo ""
    exit 1
fi

# Check if Streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo "❌ Streamlit not found!"
    echo "   Install: pip install streamlit"
    exit 1
fi

echo "✓ ngrok found"
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

# Start ngrok tunnel
echo "🌐 Starting ngrok tunnel..."
echo ""

ngrok http 8501 &
NGROK_PID=$!

sleep 3

echo "============================================================"
echo "       DEPLOYMENT SUCCESSFUL!"
echo "============================================================"
echo ""
echo "📱 Share this URL with students:"
echo ""
echo "   https://xxxx-xxxx-xxxx-xxxx.ngrok-free.app"
echo ""
echo "   (Check the ngrok window for the actual URL)"
echo ""
echo "============================================================"
echo "STUDENT INSTRUCTIONS:"
echo "============================================================"
echo "1. Open the ngrok URL in browser"
echo "2. Allow camera access when prompted"
echo "3. Enter Student ID and Name"
echo "4. Capture 3 photos"
echo "5. Click Save"
echo ""
echo "Data will be saved to your PC in: data/"
echo ""
echo "============================================================"
echo "TO STOP:"
echo "============================================================"
echo "Press Ctrl+C to stop ngrok"
echo ""
echo "To stop Streamlit, run:"
echo "  kill $STREAMLIT_PID"
echo ""
echo "Or to stop everything:"
echo "  fuser -k 8501/tcp"
echo ""
echo "============================================================"
echo ""

# Keep ngrok running
wait $NGROK_PID

# Cleanup
kill $STREAMLIT_PID 2>/dev/null
