# Face Detection App - Simple Light UI

Real-time face detection using YuNet with a clean, simple Streamlit interface.

## Project Structure

```
.
├── app.py           # Streamlit UI (camera feed + face count)
├── detector.py      # YuNet face detection logic
├── requirements.txt # Python dependencies
└── models/          # Auto-downloaded YuNet model
```

## Installation

```bash
pip install -r requirements.txt
```

## Usage

Run the application:

```bash
streamlit run app.py
```

## Features

- **Simple light mode UI** - Clean and minimal interface
- **Real-time face detection** - Green bounding boxes around faces
- **Face count** - Shows number of faces detected in sidebar
- **Cross-platform** - Works on Ubuntu and Windows
- **Auto-download** - YuNet model (337KB) downloads automatically on first run

## Camera Backends

The app automatically tries multiple backends:
- Auto (default)
- DirectShow (Windows)
- V4L2 (Linux)

## Model Info

- **YuNet**: Ultra-lightweight face detector
- **Size**: 337KB
- **Speed**: 49 FPS
- **Accuracy**: 99.6%

## Troubleshooting

**Camera not working?**
- Check camera permissions
- Ensure no other app is using the camera

**Model download fails?**
- Check internet connection
- Model auto-downloads from OpenCV Zoo
