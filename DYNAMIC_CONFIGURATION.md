# 🔧 Dynamic Configuration Guide

## ✅ **100% DYNAMIC SYSTEM - NO HARDCODED VALUES!**

This application is now fully dynamic with **ZERO hardcoded credentials, API keys, or static data**. Everything is configured through environment variables.

---

## 📋 **What's Been Made Dynamic**

### ✅ **Removed ALL Hardcoded Values:**
- ❌ No more hardcoded API keys
- ❌ No more static job listings (Wipro, TCS, etc.)
- ❌ No more predefined company data
- ❌ No more hardcoded credentials
- ❌ No more fixed model names

### ✅ **Now Everything is:**
- ✅ Configured via environment variables (.env file)
- ✅ Fetched from live APIs in real-time
- ✅ Easily changeable without code modifications
- ✅ Secure and production-ready

---

## 🔐 **Environment Variables Configuration**

### **Required Variables:**

```bash
# Django Core
SECRET_KEY=your-secret-key-change-this
DEBUG=True  # Set to False in production
ALLOWED_HOSTS=localhost,127.0.0.1

# AI Integration (REQUIRED)
GEMINI_API_KEY=your-gemini-api-key-here
# Get from: https://makersuite.google.com/app/apikey
```

### **Optional Job API Variables:**

```bash
# Adzuna API (FREE - 1000 calls/month)
ADZUNA_APP_ID=your-app-id
ADZUNA_API_KEY=your-api-key
# Sign up: https://developer.adzuna.com/

# Jooble API (FREE - 500 requests)
JOOBLE_API_KEY=your-jooble-key
# Sign up: https://jooble.org/api/about

# RapidAPI JSearch (FREE - 150 requests/month)
RAPIDAPI_KEY=your-rapidapi-key
# Sign up: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch

# Gemini Model Selection (OPTIONAL)
GEMINI_MODEL=gemini-2.0-flash
# Options: gemini-2.0-flash, gemini-1.5-pro, gemini-1.5-flash
```

**Note:** Remotive and Arbeitnow APIs don't need keys - they're FREE to use!

---

## 🚀 **How Dynamic Job Fetching Works**

### **Old System (REMOVED):**
```python
# ❌ Hardcoded jobs
jobs = [
    {"title": "Python Developer", "company": "Wipro", ...},
    {"title": "Java Developer", "company": "TCS", ...},
    # ... 15 static jobs
]
```

### **New System (CURRENT):**
```python
# ✅ Dynamic API calls
def search_indian_jobs(skills, location="India"):
    # 1. Try Remotive API (Free, no key)
    # 2. Try Arbeitnow API (Free, no key)
    # 3. Try Adzuna (if configured)
    # 4. Try Jooble (if configured)
    # Returns REAL jobs from live APIs!
```

---

## 📊 **Job API Sources (All Dynamic)**

| API | Type | Cost | API Key Needed | Jobs From |
|-----|------|------|----------------|-----------|
| **Remotive** | REST API | FREE | ❌ No | Remote tech jobs worldwide |
| **Arbeitnow** | REST API | FREE | ❌ No | European + International |
| **Adzuna** | REST API | FREE (1000/mo) | ✅ Yes | India-specific jobs |
| **Jooble** | REST API | FREE (500/mo) | ✅ Yes | Global job aggregator |
| **JSearch** | REST API | FREE (150/mo) | ✅ Yes | Indeed, LinkedIn, Glassdoor |

---

## 🔄 **How to Set Up**

### **Step 1: Copy Environment Template**
```bash
cp env.example .env
```

### **Step 2: Edit .env File**
```bash
# Edit the .env file with your actual values
nano .env  # or use any text editor
```

### **Step 3: Get API Keys (Optional but Recommended)**

1. **Adzuna API:**
   - Visit: https://developer.adzuna.com/
   - Sign up (free)
   - Get APP_ID and API_KEY
   - Add to .env file

2. **Jooble API:**
   - Visit: https://jooble.org/api/about
   - Request free API key
   - Add to .env file

3. **RapidAPI (JSearch):**
   - Visit: https://rapidapi.com/
   - Subscribe to JSearch API (free tier)
   - Get API key
   - Add to .env file

### **Step 4: Restart Server**
```bash
python manage.py runserver
```

---

## 🎯 **Benefits of Dynamic Configuration**

### **Security:**
- ✅ No credentials in source code
- ✅ .env file in .gitignore (not committed)
- ✅ Different configs for dev/staging/production

### **Flexibility:**
- ✅ Change APIs without touching code
- ✅ Easy to test different services
- ✅ Add/remove APIs anytime

### **Scalability:**
- ✅ Different configs per environment
- ✅ Easy to add new APIs
- ✅ No code changes for configuration updates

### **Real-Time Data:**
- ✅ Always fresh job listings
- ✅ No outdated information
- ✅ Automatic failover between APIs

---

## 🔍 **How Jobs Are Fetched (Step by Step)**

1. **User uploads resume** → Skills extracted (python, django, sql, etc.)

2. **System calls `search_indian_jobs(skills)`**

3. **API calls happen in parallel:**
   ```
   ├─ Remotive API      → 5 jobs
   ├─ Arbeitnow API     → 5 jobs  
   ├─ Adzuna API        → 5 jobs (if configured)
   └─ Jooble API        → 5 jobs (if configured)
   ```

4. **Deduplication:**
   - Removes duplicate jobs (same title + company)

5. **Relevance Sorting:**
   - Calculates skill matches
   - Sorts by relevance score
   - Returns top 15 best matches

6. **Result:**
   - User sees 15 most relevant, real, current jobs
   - All from live APIs
   - No static/outdated data

---

## 📝 **Configuration Files**

### **Modified Files:**
- ✅ `core/job_search.py` - ALL API keys from environment
- ✅ `core/utils.py` - Gemini model configurable
- ✅ `env.example` - Complete configuration template
- ✅ `.gitignore` - Ensures .env not committed

### **How to Verify No Hardcoded Values:**
```bash
# Search for any remaining hardcoded API keys
grep -r "AIzaSy" .  # Should return nothing
grep -r "api_key.*=.*\"" core/  # Should only show os.getenv()
```

---

## 🛠️ **Troubleshooting**

### **No Jobs Appearing:**
1. Check if any API keys are configured:
   ```bash
   cat .env | grep API_KEY
   ```

2. Check logs for API errors:
   ```bash
   tail -f logs/django.log
   ```

3. Test individual APIs:
   - Remotive: Works without key ✅
   - Arbeitnow: Works without key ✅
   - Others: Need API keys

### **API Rate Limits:**
- **Remotive:** No limit (free)
- **Arbeitnow:** No limit (free)
- **Adzuna:** 1000 calls/month
- **Jooble:** 500 requests/month
- **JSearch:** 150 requests/month

---

## ✅ **Verification Checklist**

- [ ] No hardcoded API keys in code
- [ ] All credentials in .env file
- [ ] .env file in .gitignore
- [ ] env.example template updated
- [ ] System fetches jobs from live APIs
- [ ] No static job listings
- [ ] Deduplication working
- [ ] Relevance sorting working
- [ ] Logs show API calls

---

## 🎉 **Success!**

Your system is now **100% dynamic** with:
- ✅ Zero hardcoded values
- ✅ All configuration via environment variables
- ✅ Real-time job fetching from multiple APIs
- ✅ Production-ready security
- ✅ Easy to scale and maintain

**Everything is configurable, nothing is hardcoded!** 🚀
