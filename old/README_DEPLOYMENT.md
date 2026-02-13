# Face Enrollment - Deployment Guide

## For Students: How to Enroll Your Face

### Option 1: ngrok Tunnel (Recommended)

**Teacher provides a URL like:**
```
https://abcd-1234-5678.ngrok-free.app
```

**Steps:**
1. **Open the URL** in your browser (Chrome/Firefox/Safari)
2. **Allow camera access** when browser prompts
3. **Click "START ENROLLMENT"**
4. **Enter your Student ID** (e.g., 101, 102)
5. **Enter your Full Name**
6. **Click "Next"**
7. **Click "Start Camera"**
8. **Position your face:**
   - Center your face in the frame
   - Keep good lighting on your face
   - Stay about 1-2 feet from camera
   - Wait for green box (not red)
9. **Click "Capture Photo"** 3 times
   - Move slightly between photos
   - Different angles are OK
10. **Click "Done - Save"**
11. **Review your info** and click "Save Enrollment"
12. **Done!** Your data is saved

### Option 2: Cloudflare Tunnel

**Teacher provides a URL like:**
```
https://xyzabc.trycloudflare.com
```

**Same steps as above!**

### Option 3: Local Network (Same WiFi)

**Teacher provides URL like:**
```
http://192.168.1.100:8501
```

**Same steps as above!**

---

## For Teacher: How to Deploy

### Option 1: ngrok (Recommended)

**Step 1: Install ngrok**
```bash
# Download from: https://ngrok.com/download
# Or on Linux:
sudo apt install ngrok  # (if available)
# Or:
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
unzip ngrok-v3-stable-linux-amd64.tgz
sudo mv ngrok /usr/local/bin/
```

**Step 2: Run deployment script**
```bash
chmod +x deploy_ngrok.sh
./deploy_ngrok.sh
```

**Step 3: Share the URL**
- Look for: `https://xxxx-xxxx-xxxx.ngrok-free.app`
- Share this URL with students
- URL changes each time you restart ngrok

**Step 4: Monitor**
- Keep the terminal open
- You'll see ngrok showing connection info

**Step 5: Stop**
- Press `Ctrl+C` in the ngrok terminal

### Option 2: Cloudflare Tunnel (No Account Needed)

**Step 1: Install cloudflared**
```bash
# For Linux (Debian/Ubuntu)
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb
```

**Step 2: Run deployment script**
```bash
chmod +x deploy_cloudflare.sh
./deploy_cloudflare.sh
```

**Step 3: Share the URL**
- Look for: `https://xxxxx.trycloudflare.com`
- Share this URL with students
- URL changes each time you restart

### Option 3: Local Network Only

**Step 1: Find your IP**
```bash
# Linux
hostname -I

# Or
ip addr show | grep inet
```

**Step 2: Run Streamlit**
```bash
streamlit run enrollment_app.py --server.port 8501
```

**Step 3: Share URL**
- Format: `http://YOUR-IP:8501`
- Example: `http://192.168.1.100:8501`
- Students must be on same WiFi/network

---

## Troubleshooting

### Students: Camera Not Working

**Problem:** Browser denies camera access
**Solution:**
1. Check URL bar for camera icon
2. Click it and "Allow"
3. Refresh page
4. Or try different browser (Chrome recommended)

### Students: "No face detected"

**Problem:** Face not recognized
**Solution:**
1. Move closer to camera
2. Improve lighting (face should be bright)
3. Center your face in frame
4. Look directly at camera
5. Remove glasses if possible

### Teacher: Port 8501 already in use

**Problem:** Another app using port 8501
**Solution:**
```bash
# Kill process on port 8501
fuser -k 8501/tcp

# Or use different port
streamlit run enrollment_app.py --server.port 8502
```

### Teacher: ngrok shows "Account exceeded limit"

**Problem:** Free tier has limits
**Solution:**
1. Use Cloudflare tunnel instead (no account needed)
2. Or wait and restart ngrok later
3. Or use local network option

---

## Security Tips

### For Teacher:

✅ **Keep deployment running only when needed**
- Start before enrollment period
- Stop after enrollment done

✅ **Monitor connections** (ngrok shows this)
- Check how many students are connected
- Look for unusual activity

✅ **Use in secure location**
- Don't leave running unattended
- Students should enroll themselves

✅ **Backup data regularly**
```bash
# Backup embeddings
cp -r data/ data_backup_$(date +%Y%m%d)/
```

### For Students:

✅ **Only enroll your own face**
- Don't enroll others
- Use your correct Student ID

✅ **Use good photos**
- Clear face photos work better
- Multiple angles improve recognition

---

## Data Location

All enrolled student data is saved on teacher's PC:

```
data/
├── embeddings/
│   └── embeddings.json          # Face recognition data
├── metadata/
│   └── student_info.json        # Student information
└── photos/
    ├── 101/
    │   ├── photo_1.jpg
    │   ├── photo_2.jpg
    │   └── photo_3.jpg
    └── 102/
        └── ...
```

---

## Need Help?

**Common Issues:**
1. **Camera not working** → Check browser permissions
2. **No face detected** → Improve lighting, move closer
3. **Can't access URL** → Check if teacher's deployment is running
4. **Save failed** → Try again, check internet connection

**Contact your teacher if issues persist!**
