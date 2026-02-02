# Production Fix: Missing PDF Extraction Libraries

## Issue
Production server is missing required PDF extraction libraries:
- `PyPDF2` - No module named 'PyPDF2'
- `pdfplumber` - No module named 'pdfplumber'
- `pdfminer` - No module named 'pdfminer'

## Solution

### On Production Server

1. **SSH into the production server:**
   ```bash
   ssh root@srv1217187
   ```

2. **Navigate to the project directory:**
   ```bash
   cd /var/www/prozlab_ai
   ```

3. **Activate the virtual environment:**
   ```bash
   source venv/bin/activate
   ```

4. **Install the missing dependencies:**
   ```bash
   pip install PyPDF2>=3.0.0 pdfminer.six>=20240706 pdfplumber>=0.11.4
   ```
   
   OR install all requirements:
   ```bash
   pip install -r requirements.txt
   ```

5. **Restart the backend service:**
   ```bash
   service prozlab_backend restart
   ```

6. **Verify the installation:**
   ```bash
   python -c "import PyPDF2; import pdfplumber; from pdfminer.high_level import extract_text; print('All PDF libraries installed successfully')"
   ```

## Additional Issue: OpenAI Rate Limit (429)

The logs also show:
```
OpenAI API error 429
```

This is a **rate limit** error (different from quota exceeded). This means:
- Too many requests in a short time
- The service will fall back to heuristic analysis
- **No action needed** - the service handles this gracefully

## Verification

After installing the libraries, test the endpoint:
```bash
curl -X POST https://app.prozlab.com/api/v1/proz/ai/parse-resume \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@test_resume.pdf"
```

Expected: Should return 200 OK with extracted resume data (using heuristic analysis if OpenAI is rate-limited).

## Quick Fix Script

You can run this on the production server:

```bash
#!/bin/bash
cd /var/www/prozlab_ai
source venv/bin/activate
pip install PyPDF2>=3.0.0 pdfminer.six>=20240706 pdfplumber>=0.11.4
service prozlab_backend restart
echo "PDF libraries installed and service restarted"
```
