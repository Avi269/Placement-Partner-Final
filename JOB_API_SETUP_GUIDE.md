# 🔑 Job API Setup Guide - Multiple Fallback Options

Your Placement Partner project now supports **7 different job APIs** with automatic fallback!

---

## ✅ **CURRENTLY ACTIVE APIs:**

### 1. **Curated Indian Jobs** ⭐ (ACTIVE)
- **Status:** ✅ Working
- **Cost:** FREE (Built-in database)
- **Jobs:** 80+ real Indian tech jobs
- **Companies:** Wipro, TCS, Infosys, Flipkart, Amazon, Swiggy, etc.
- **Setup:** No setup needed

### 2. **Adzuna API** ⭐ (ACTIVE)
- **Status:** ✅ Working & Configured
- **Cost:** FREE (1000 calls/month)
- **App ID:** `f761347b`
- **API Key:** `0ba8ad53f5abdb403cefd231bbe6ebc4`
- **Coverage:** India + 20+ countries
- **Aggregates:** Jobs from multiple sources including Naukri

### 3. **Remotive API** ⭐ (ACTIVE)
- **Status:** ✅ Working
- **Cost:** FREE (Unlimited)
- **Setup:** No API key needed
- **Coverage:** Remote tech jobs worldwide
- **URL:** https://remotive.com/api/remote-jobs

### 4. **Arbeitnow API** ⭐ (ACTIVE)
- **Status:** ✅ Working
- **Cost:** FREE
- **Setup:** No API key needed
- **Coverage:** Tech jobs globally
- **URL:** https://www.arbeitnow.com/api/job-board-api

---

## 🆕 **NEW FALLBACK APIs (Need Setup):**

### 5. **JSearch API (RapidAPI)** - Multi-Source Aggregator
**Aggregates from:** Indeed, LinkedIn, Glassdoor, ZipRecruiter

**How to Setup:**
1. Go to: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
2. Click "Sign Up" (use Google/GitHub)
3. Subscribe to "Basic Plan" (FREE - 150 requests/month)
4. Copy your RapidAPI Key from dashboard
5. Update in `core/job_search.py`:
   ```python
   self.rapidapi_key = "YOUR_KEY_HERE"
   ```

**Why use it?**
- Aggregates multiple job boards (Indeed, LinkedIn, Glassdoor)
- 150 free searches/month
- India support
- Instant approval

---

### 6. **The Muse API** - Remote & Culture-Focused
**Status:** Ready to use (No API key needed!)

**How to Setup:**
- Already integrated! No setup required
- Public API access
- Focus on remote jobs & company culture

**Why use it?**
- FREE unlimited access
- No API key needed
- Quality remote-friendly jobs
- Company culture information

---

### 7. **Jooble API** - India Support
**Coverage:** India, USA, UK, and 70+ countries

**How to Setup:**
1. Go to: https://jooble.org/api/about
2. Fill the registration form:
   - Name: Your name
   - Email: Your email
   - Website: http://localhost:8000
   - Description: "Educational placement platform for students"
3. Wait for API key email (usually instant)
4. Update in `core/job_search.py`:
   ```python
   self.jooble_api_key = "YOUR_KEY_HERE"
   ```

**Why use it?**
- 1000 free requests per DAY
- Strong India support
- Fast approval

---

## 🎯 **RECOMMENDED SETUP ORDER:**

### **Priority 1: Already Done! ✅**
- ✅ Curated Indian Jobs
- ✅ Adzuna API
- ✅ Remotive API
- ✅ Arbeitnow API

**You currently have 4 working APIs!**

### **Priority 2: Quick Wins (5 minutes each)**
1. **RapidAPI JSearch** (Adds Indeed, LinkedIn, Glassdoor)
   - Sign up: https://rapidapi.com/
   - Subscribe to JSearch API (free plan)
   - Add API key to code

2. **Jooble** (Adds 1000 daily searches for Indian jobs)
   - Sign up: https://jooble.org/api/about
   - Get instant API key
   - Add to code

### **Priority 3: Optional**
- The Muse is already integrated (no setup needed)

---

## 🔄 **How Fallback System Works:**

```
User searches for jobs
         ↓
1. Curated Indian Jobs (Always first)
         ↓ (if < 3 jobs)
2. Adzuna API (India jobs)
         ↓ (if < 5 jobs)
3. Remotive API (Remote jobs)
         ↓ (if < 5 jobs)
4. Arbeitnow API (Tech jobs)
         ↓ (if < 5 jobs)
5. JSearch API (Indeed, LinkedIn, Glassdoor)
         ↓ (if < 5 jobs)
6. The Muse API (Remote jobs)
         ↓ (if < 5 jobs)
7. Jooble API (Indian jobs)
         ↓
Return best matched jobs
```

**Result:** You'll always have job listings, even if one API fails!

---

## 📊 **API Comparison Table:**

| API | Setup Time | Free Tier | India Jobs | Status |
|-----|-----------|-----------|------------|---------|
| Curated Database | 0 min | Unlimited | ✅ Yes | ✅ Active |
| Adzuna | Done ✅ | 1000/month | ✅ Yes | ✅ Active |
| Remotive | 0 min | Unlimited | Remote | ✅ Active |
| Arbeitnow | 0 min | Unlimited | Tech Jobs | ✅ Active |
| JSearch (RapidAPI) | 5 min | 150/month | ✅ Yes | ⚠️ Need key |
| The Muse | 0 min | Unlimited | Remote | ✅ Active |
| Jooble | 5 min | 1000/day | ✅ Yes | ⚠️ Need key |

---

## 🚀 **Quick Start Commands:**

### Test Current Setup (4 APIs working):
```bash
cd Placement_Partner
python test_adzuna.py
```

### Test After Adding New APIs:
```python
from core.job_search import fetch_jobs_for_skills

# This will use all available APIs
jobs = fetch_jobs_for_skills(['python', 'django'], location='in', max_results=20)
print(f"Found {len(jobs)} jobs from multiple sources")
```

---

## 💡 **Tips:**

1. **You already have 4 working APIs** - Your project is functional now!
2. **Add JSearch** - Best for aggregating Indeed/LinkedIn (5 min setup)
3. **Add Jooble** - Best for high volume Indian jobs (5 min setup)
4. **The Muse** - Already works, no action needed
5. **Keep API keys secure** - Don't commit to Git

---

## 🔐 **Security Best Practice:**

After getting API keys, store them in environment variables:

1. Create `.env` file:
```bash
ADZUNA_APP_ID=f761347b
ADZUNA_API_KEY=0ba8ad53f5abdb403cefd231bbe6ebc4
RAPIDAPI_KEY=your_rapidapi_key_here
JOOBLE_API_KEY=your_jooble_key_here
```

2. Install python-decouple:
```bash
pip install python-decouple
```

3. Update code to read from .env:
```python
from decouple import config
self.rapidapi_key = config('RAPIDAPI_KEY', default='PASTE_YOUR_RAPIDAPI_KEY_HERE')
```

---

## ✅ **Your System Status:**

**Currently Active:** 4/7 APIs ✅
**Job Sources:** Curated DB + Adzuna + Remotive + Arbeitnow
**Monthly Capacity:** 1000+ job searches
**Fallback Layers:** 4 levels of redundancy

**You're ready to go! 🎉**

Add JSearch and Jooble for even more coverage (10 minutes total).
