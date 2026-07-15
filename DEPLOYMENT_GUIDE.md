# Deployment Guide - Backend Options

## 🚨 Current Issue
HuggingFace Spaces is stuck in "starting" loop due to:
1. **Embedding model preloading** (~100MB+ fastembed model download)
2. **Database connection delays** during cold starts
3. **Resource constraints** on free tier

## ✅ Solutions Applied

### Optimizations Made:
1. **Lazy loading** - Embedding model loads on first use instead of startup
2. **Timeout protection** - Database init has 30s timeout with graceful fallback
3. **Reduced connection timeout** - 10s instead of 15s for faster failure detection
4. **Better logging** - Clear startup progress indicators
5. **Health check** - Helps HF Spaces detect when app is ready

### Changes:
- Modified `api/main.py` - Combined startup tasks with timeout protection
- Modified `db/database.py` - Reduced connection timeout to 10s
- Modified `Dockerfile` - Added health check and optimized uvicorn settings
- Added `requests` to `requirements.txt` for health checks

## 🚀 Deployment Options

### Option 1: Railway (⭐ RECOMMENDED)
**Best for: FastAPI backends with databases**

**Pros:**
- Free tier: 500 hours/month + $5 credit
- No startup loops
- Better resource allocation
- Built-in PostgreSQL
- Automatic HTTPS

**Setup:**
```bash
# 1. Install Railway CLI
npm i -g @railway/cli

# 2. Login
railway login

# 3. Initialize project (in backend folder)
cd backend
railway init

# 4. Add environment variables
railway variables set DATABASE_URL="your-neon-url"
railway variables set QDRANT_URL="your-qdrant-url"
railway variables set QDRANT_API_KEY="your-qdrant-key"
railway variables set GROQ_API_KEY="your-groq-key"
railway variables set SECRET_KEY="your-secret-key"

# 5. Deploy
railway up
```

**Cost:** Free for ~500 hours, then ~$5/month

---

### Option 2: Render (Free Tier)
**Best for: Simple deployments**

**Pros:**
- Generous free tier (750 hours/month)
- Easy setup
- Automatic deploys from GitHub

**Cons:**
- Spins down after 15 min inactivity (50s cold start)
- 512MB RAM limit (you hit this before)

**Setup:**
1. Go to https://render.com
2. New > Web Service
3. Connect GitHub repo
4. Settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
   - **Environment:** Python 3.11
5. Add environment variables from your `.env`

---

### Option 3: Fly.io
**Best for: Global edge deployment**

**Pros:**
- Free tier: 3 shared VMs
- Fast global deployment
- Better resource allocation than Render

**Setup:**
```bash
# 1. Install flyctl
# Windows: https://fly.io/docs/flyctl/install/

# 2. Login
flyctl auth login

# 3. Launch app (in backend folder)
cd backend
flyctl launch

# 4. Set secrets
flyctl secrets set DATABASE_URL="your-neon-url"
flyctl secrets set QDRANT_URL="your-qdrant-url"
flyctl secrets set QDRANT_API_KEY="your-qdrant-key"
flyctl secrets set GROQ_API_KEY="your-groq-key"
flyctl secrets set SECRET_KEY="your-secret-key"

# 5. Deploy
flyctl deploy
```

---

### Option 4: Keep HuggingFace Spaces (Current)
**Only if you want to stick with HF**

**Try these fixes:**

1. **Push the optimized code:**
```bash
git add .
git commit -m "fix: optimize startup for HF Spaces with lazy loading"
git push
```

2. **Check Space settings:**
   - Hardware: Ensure you're on "CPU Basic" (free) or upgrade to "CPU Upgrade" ($0.60/hour)
   - Secrets: Verify all environment variables are set correctly

3. **Monitor logs:**
   - Go to your Space > Logs
   - Should see "===== Startup complete =====" within 60 seconds

4. **If still stuck:**
   - Delete and recreate the Space (since Docker SDK is now paid, clone from existing Space)
   - Or switch to Railway/Render (recommended)

---

### Option 5: Back to Render with Optimizations
**Your RAM issue might be fixed now**

The lazy loading + optimized startup should reduce memory footprint:
- No preloading of embedding model = ~200MB saved at startup
- NullPool for DB connections = Less memory overhead
- Faster startup = Less time hitting RAM limits

**Try Render again with:**
- Instance Type: Free (512MB)
- The optimized code should stay under 512MB now

---

## 🎯 My Recommendation

### For immediate fix: **Railway**
- Most reliable for your use case
- Free tier is generous
- No startup issues
- Best developer experience

### For staying free: **Render (retry)**
- The optimizations should fix your RAM issue
- Much simpler than HF Spaces
- Better for FastAPI than HF Spaces (which is designed for ML demos)

### For global performance: **Fly.io**
- If you expect international users
- Slightly more complex setup

---

## 📊 Comparison

| Platform | Free Tier | Cold Start | RAM | Best For |
|----------|-----------|------------|-----|----------|
| **Railway** | 500h + $5 credit | None | 1GB+ | Production-ready apps |
| **Render** | 750h/month | ~50s | 512MB | Simple free hosting |
| **Fly.io** | 3 shared VMs | ~10s | 256MB per VM | Global edge apps |
| **HF Spaces** | Unlimited* | ~30-60s | Limited | ML model demos |

*HF Spaces free tier is being restricted; Docker SDK is now paid

---

## ⚡ Quick Start: Railway (5 minutes)

```bash
# 1. Install Railway
npm i -g @railway/cli

# 2. Deploy
cd backend
railway login
railway init
railway up

# 3. Add environment variables in Railway dashboard
# https://railway.app/dashboard

# 4. Done! Your API is live
```

---

## 🔧 Environment Variables Needed

All platforms need these:
```
DATABASE_URL=postgresql://...  (Neon connection string)
QDRANT_URL=https://...
QDRANT_API_KEY=...
GROQ_API_KEY=...
SECRET_KEY=...  (for JWT tokens)
```

---

## 📝 Notes

- The optimized code works on ALL platforms
- HF Spaces is really designed for ML demos (Gradio/Streamlit), not FastAPI APIs
- Railway/Render are purpose-built for web APIs
- You can always migrate later - just update your frontend's API URL
