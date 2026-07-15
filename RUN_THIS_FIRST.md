# 🚨 IMPORTANT: Run This First!

## Before the "Try Demo" button works, you MUST run this database migration:

### Option 1: Using psql command line

```bash
psql "postgresql://neondb_owner:npg_wUESp6Mhndi0@ep-winter-mountain-att3iz8o-pooler.c-9.us-east-1.aws.neon.tech/neondb?sslmode=require" -c "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_guest BOOLEAN DEFAULT FALSE NOT NULL; CREATE INDEX IF NOT EXISTS idx_users_is_guest_created ON users(is_guest, created_at) WHERE is_guest = TRUE;"
```

### Option 2: Using Neon Dashboard

1. Go to https://console.neon.tech
2. Select your project
3. Click "SQL Editor"
4. Run this SQL:

```sql
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS is_guest BOOLEAN DEFAULT FALSE NOT NULL;

CREATE INDEX IF NOT EXISTS idx_users_is_guest_created 
ON users(is_guest, created_at) 
WHERE is_guest = TRUE;
```

5. Click "Run"

### Option 3: Using the migration file

```bash
cd backend
psql $DATABASE_URL -f migrations/001_add_is_guest_column.sql
```

---

## After running migration:

### Test the backend:

Go to your HuggingFace Space and test:
```
https://9raveen-multi-agent-rag-research-assistant-api.hf.space/auth/guest
```

Should return something like:
```json
{
  "id": "...",
  "email": "guest_abc123...@demo.local",
  "access_token": "eyJ...",
  "is_guest": true
}
```

### Deploy frontend:

```bash
cd frontend
npm run build
vercel --prod
```

Or just push to GitHub and Vercel will auto-deploy:
```bash
git push origin main
```

---

## ✅ Checklist:

- [ ] Run database migration (add `is_guest` column)
- [ ] Test `/auth/guest` endpoint on HF Spaces
- [ ] Deploy frontend to Vercel
- [ ] Test "Try Demo" button on your live site
- [ ] Setup cleanup cron job (optional, can do later)

---

## Where to find the Try Demo button:

1. Visit your Vercel frontend URL
2. You'll see the auth page (login/signup)
3. **The "Try Demo" button is below the form** with a purple gradient
4. Click it → instantly logged in as guest
5. Yellow banner appears at top: "🧪 Demo Mode"

---

## If something doesn't work:

1. **Backend error**: Check HF Spaces logs
2. **Frontend error**: Check browser console (F12)
3. **Migration error**: Make sure you're connected to the right database
4. **Button not showing**: Make sure you deployed the latest frontend code

---

## Quick verification:

```bash
# Check if migration ran successfully
psql $DATABASE_URL -c "SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='is_guest';"

# Should return: is_guest
```

---

**That's it! Once the migration is done, the Try Demo feature is fully functional.** 🎉
