# Facial recognition attendance system

### what we want (proposal)

we want a full system where the user (teacher/lecturer) will shoot a small  ~10 sec video of the class (including all present students) and it will be uploaded on a web application (responsive for mobiles). From here frames (having most students clearly) will be extracted and those frames will be given to the ML model which will recognize the student and out their name/id which then can be marked present on that day.

---
# 🚀 2-WEEK FACIAL RECOGNITION ATTENDANCE SYSTEM

## Team Execution Plan - Analysis & Technical Proposal

---

## 📊 PROJECT ANALYSIS

### **Feasibility: ✅ 100% ACHIEVABLE**

**Why this works:**

- YuNet (337KB) + SFace (5MB) = Ultra-lightweight stack
- Processing time: <1 second per 10-sec video
- Memory: <800MB VRAM (fits easily on 4GB GPU)
- Team-based parallel development: 4-6 people working simultaneously
- Proven architecture: Both models are production-ready

**Risk Assessment:**

| Risk                      | Probability | Mitigation                                 |
| ------------------------- | ----------- | ------------------------------------------ |
| Model accuracy low        | Low         | Enroll 5 photos per student instead of 3   |
| GPU VRAM overflow         | Very Low    | Batch processing ensures <500MB peak usage |
| Frontend-backend mismatch | Low         | Freeze API contract on Day 3               |
| Time pressure on Week 2   | Medium      | Pre-planned parallel work streams          |
|                           |             |                                            |

---

## 🏗️ TECHNICAL ARCHITECTURE

```
┌─────────────────────────────────────────┐
│          TEACHER UPLOADS VIDEO (10sec)  │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│   FRAME EXTRACTION (Every 10th frame)   │
│   30 frames total from 300 total frames │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│   BATCH FACE DETECTION (YuNet)          │
│   4-8 frames per batch                  │
│   <50ms per frame                       │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│   FACE ALIGNMENT & CROPPING             │
│   Using 5-point landmarks from YuNet    │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│   EMBEDDING GENERATION (SFace)          │
│   128-dimensional vectors               │
│   <10ms per face                        │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│   COSINE SIMILARITY MATCHING            │
│   Compare against all registered faces  │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│   VOTING SYSTEM (60% Consensus)         │
│   Mark present if 60%+ frames agree     │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│   SAVE ATTENDANCE + RETURN RESULTS      │
│   JSON response with present/absent     │
└─────────────────────────────────────────┘
```

### **Model Specifications**

|Component|Model|Size|Speed|Accuracy|
|---|---|---|---|---|
|**Detection**|YuNet|337KB|49 FPS (CPU)|99.6% on test set|
|**Recognition**|SFace|5MB|100 FPS|99.4% on LFW|
|**Total Models**|-|5.3MB|<1sec/video|>95% end-to-end|

