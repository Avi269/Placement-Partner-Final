# 🚀 Complete Ollama Setup Guide

## Step 1: Install Ollama

### For Windows:
1. **Download Ollama:**
   - Visit: https://ollama.ai/download/windows
   - OR direct link: https://ollama.ai/download/OllamaSetup.exe

2. **Install:**
   - Run the downloaded installer
   - Click through the installation wizard
   - Ollama will start automatically as a service

3. **Verify Installation:**
   ```powershell
   ollama --version
   ```
   You should see: `ollama version is X.X.X`

---

## Step 2: Download a Model

### Recommended Models:

**For Best Quality (Recommended):**
```powershell
ollama pull mistral
```
- Size: ~4GB
- Quality: Excellent
- Speed: Fast

**For Smaller/Faster:**
```powershell
ollama pull phi
```
- Size: ~1.6GB
- Quality: Good
- Speed: Very fast

**For Code-Focused:**
```powershell
ollama pull codellama
```
- Size: ~3.8GB
- Quality: Excellent for code
- Speed: Fast

---

## Step 3: Verify Ollama is Running

```powershell
# Test if Ollama server is running
curl http://localhost:11434/api/tags

# OR test with a simple prompt
ollama run mistral "Hello, world!"
```

---

## Step 4: Install Python Dependencies

```powershell
cd c:\Users\habib\OneDrive\Desktop\PLACEMENT\Placement_Partner
pip install requests
```

---

## Step 5: Your Code is Ready!

✅ I've already updated your code to use Ollama!

The system will now:
1. Try Ollama FIRST (your local FREE model)
2. Fallback to Gemini API if Ollama isn't available
3. Work completely offline once Ollama is set up

---

## Step 6: Start Your Server

```powershell
cd c:\Users\habib\OneDrive\Desktop\PLACEMENT\Placement_Partner
python manage.py runserver
```

You should see:
```
✓ Ollama backend initialized successfully
✓ Auto-selected backend: ollama
✓ Using AI model backend: ollama
```

---

## Testing Your Setup

### Test 1: Check if Ollama is Running
```powershell
ollama list
```
Should show: `mistral` or `phi` or whichever model you downloaded

### Test 2: Test Model Directly
```powershell
ollama run mistral "Extract name from: John Doe, john@email.com"
```

### Test 3: Upload Resume
1. Go to: http://127.0.0.1:8000/resume/
2. Upload a test resume
3. Should work WITHOUT any API key!

---

## What You Get

✅ **FREE forever** - No API costs
✅ **Local processing** - Data never leaves your computer
✅ **No internet needed** - After initial model download
✅ **Privacy-first** - Your data stays private
✅ **Fast** - No network latency
✅ **Unlimited usage** - No rate limits or quotas

---

## Troubleshooting

### Issue: "ollama command not found"
**Solution:** Restart your terminal after installation, or add Ollama to PATH:
```powershell
$env:Path += ";C:\Users\$env:USERNAME\AppData\Local\Programs\Ollama"
```

### Issue: "Ollama not available"
**Solution:** Make sure Ollama service is running:
```powershell
# Check if running
Get-Service Ollama

# Start service if needed
Start-Service Ollama
```

### Issue: "Connection refused to localhost:11434"
**Solution:** Restart Ollama:
```powershell
# Stop and start Ollama service
Restart-Service Ollama
```

### Issue: "Model not found"
**Solution:** Download the model:
```powershell
ollama pull mistral
```

---

## Model Comparison

| Model | Size | Best For | Speed |
|-------|------|----------|-------|
| **mistral** | 4GB | General use, best quality | Fast |
| **phi** | 1.6GB | Small systems, testing | Very fast |
| **llama2** | 3.8GB | Good balance | Fast |
| **codellama** | 3.8GB | Code-heavy resumes | Fast |
| **neural-chat** | 4.1GB | Conversational tasks | Fast |

---

## System Requirements

**Minimum:**
- 8GB RAM
- 10GB free disk space
- Windows 10/11

**Recommended:**
- 16GB RAM
- 20GB free disk space
- Windows 11

---

## Quick Command Reference

```powershell
# Check Ollama version
ollama --version

# List installed models
ollama list

# Download a model
ollama pull mistral

# Test a model
ollama run mistral "test prompt"

# Remove a model (to save space)
ollama rm phi

# Check Ollama service status
Get-Service Ollama

# View Ollama logs (if issues)
Get-Content "$env:LOCALAPPDATA\Ollama\logs\server.log" -Tail 50
```

---

## What Happens Now

When you start your Django server:

1. System checks for Ollama on localhost:11434
2. If found, loads "mistral" model
3. All resume parsing uses Ollama (FREE, local)
4. No API key needed
5. No internet required
6. No costs ever!

---

## Next Steps

1. **Install Ollama:** Download from https://ollama.ai/
2. **Pull model:** `ollama pull mistral`
3. **Start server:** `python manage.py runserver`
4. **Test:** Upload a resume at http://127.0.0.1:8000/resume/

---

## 🎉 You're Done!

Your system will now:
- ✅ Use FREE Ollama model
- ✅ Work completely offline
- ✅ Keep all data private
- ✅ Have no API costs
- ✅ Run unlimited resume parsing

**Enjoy your FREE, privacy-first resume parser!** 🚀
