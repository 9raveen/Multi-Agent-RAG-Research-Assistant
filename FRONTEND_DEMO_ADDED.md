# ✅ Try Demo Button - Frontend Implementation Complete

## What Was Added

### 1. **API Function** (`frontend/src/api.js`)
```javascript
export async function createGuestAccount()
```
- Calls `POST /auth/guest` endpoint
- Stores auth token in sessionStorage
- Marks user as guest with `is_guest` flag

### 2. **Auth Context** (`frontend/src/context/AuthContext.jsx`)
```javascript
const tryDemo = useCallback(async () => {
  const u = await api.createGuestAccount();
  setUser(u);
  return u;
}, []);
```
- Added `tryDemo` function to context
- Available alongside `login` and `signup`

### 3. **Try Demo Button** (`frontend/src/components/AuthPage.jsx`)
- Added below the login/signup form
- Purple gradient button: 🚀 Try Demo
- Subtitle: "No signup required • Full access • 24 hour workspace"
- Disabled state while creating demo account
- Error handling for failed demo creation

### 4. **Guest Banner** (`frontend/src/components/GuestBanner.jsx`)
- Shows at top of app when in demo mode
- Yellow/amber gradient background
- Message: "🧪 Demo Mode • Your workspace will be deleted in 24 hours"
- "Create Permanent Account" button
- Sticky positioning (always visible)
- Responsive design (stacks on mobile)

### 5. **Styling**
- `AuthPage.css` - Demo button and divider styles
- `GuestBanner.css` - Banner component styles
- Both support light/dark themes
- Smooth transitions and hover effects

## Where to Find It

### Login Page
1. Visit your deployed frontend (Vercel)
2. See the auth page with login/signup form
3. **"Try Demo" button is below the form** with an "or" divider
4. Click it → instantly logged in as guest

### Guest Banner
1. After clicking "Try Demo", you're logged in
2. **Yellow banner appears at the top** of the workspace
3. Shows "Demo Mode" with expiration reminder
4. Click "Create Permanent Account" to sign up

## Visual Layout

```
┌─────────────────────────────────────────┐
│          AUTH PAGE (Login/Signup)        │
├─────────────────────────────────────────┤
│  [Email Input]                          │
│  [Password Input]                       │
│  [Sign in Button]                       │
│                                         │
│  ───────────── or ─────────────         │
│                                         │
│  [🚀 Try Demo]  ← NEW!                  │
│  No signup • Full access • 24h          │
│                                         │
│  New to MARA? Create one               │
└─────────────────────────────────────────┘

After clicking Try Demo:

┌─────────────────────────────────────────┐
│ 🧪 Demo Mode • Data expires in 24h     │
│            [Create Permanent Account]   │ ← NEW!
├─────────────────────────────────────────┤
│                                         │
│         Your Workspace                  │
│         (Upload, Chat, etc.)            │
│                                         │
└─────────────────────────────────────────┘
```

## Testing

### 1. Local Testing
```bash
cd frontend
npm run dev
```

Visit http://localhost:5173 and:
- ✅ See "Try Demo" button on auth page
- ✅ Click it → should create guest account
- ✅ See yellow guest banner at top
- ✅ Can upload PDFs and query
- ✅ Click "Create Permanent Account" → logs out and shows auth page

### 2. Production Testing (After Deploy)

**Before deploying, you need to:**

1. **Run database migration** (Add `is_guest` column):
   ```sql
   ALTER TABLE users ADD COLUMN is_guest BOOLEAN DEFAULT FALSE NOT NULL;
   ```

2. **Deploy frontend** to Vercel:
   ```bash
   cd frontend
   npm run build
   vercel --prod
   ```

3. **Test the flow:**
   - Visit your Vercel URL
   - Click "Try Demo"
   - Upload a document
   - Ask a question
   - Verify data isolation (create another guest, they shouldn't see first guest's docs)

## Next Steps

### Required (Before Going Live)

1. **Run Database Migration**
   ```bash
   psql $DATABASE_URL -f backend/migrations/001_add_is_guest_column.sql
   ```

2. **Deploy Frontend to Vercel**
   ```bash
   cd frontend
   git pull origin main  # Get latest changes
   vercel --prod
   ```

3. **Setup Cleanup Cron Job**
   ```bash
   # On Railway or Render, schedule:
   python backend/cleanup_guests.py
   # To run daily at 2am
   ```

4. **Test End-to-End**
   - Create guest account
   - Upload PDF
   - Query it
   - Wait 5 minutes, run cleanup with `--age-hours 0`
   - Verify guest account is deleted

### Optional Enhancements

1. **Pre-load Demo Document**
   - Add a sample research paper to guest accounts automatically
   - Users can start querying immediately

2. **Progress Indicator**
   - Show "Creating your demo workspace..." with animation
   - Better UX for slower connections

3. **Guest Usage Analytics**
   - Track how many guests convert to permanent
   - Monitor average documents uploaded per guest
   - See most common queries in demo mode

4. **Rate Limiting**
   - Limit guests to 3 documents
   - Show upgrade prompt when hitting limit

## Troubleshooting

### "Try Demo" button not appearing
- Check `frontend/src/components/AuthPage.jsx` imports
- Verify `tryDemo` is in AuthContext provider value
- Check browser console for errors

### "Failed to create demo account"
- Check backend logs - is `/auth/guest` endpoint working?
- Verify database has `is_guest` column
- Check CORS settings allow your frontend domain

### Guest banner not showing
- Check if `sessionStorage.getItem("is_guest")` returns `"true"`
- Verify `<GuestBanner />` is in `App.jsx`
- Check browser console for errors

### Demo account can see other users' documents
- This is a serious bug! Check:
  - Backend filters by `user_id` in retrieval
  - Qdrant points have `user_id` in payload
  - Database queries include `user_id` filter

## Features Summary

✅ **Try Demo Button** - One-click guest account creation
✅ **Guest Banner** - Persistent reminder about expiration
✅ **Full Isolation** - Each guest has own workspace
✅ **No PII Collected** - Fake emails (guest_xxx@demo.local)
✅ **Auto Cleanup** - 24-hour expiration
✅ **Easy Conversion** - One-click to create permanent account
✅ **Responsive Design** - Works on mobile and desktop
✅ **Theme Support** - Light and dark mode
✅ **Error Handling** - Graceful failures with user feedback

## Current Status

- ✅ Backend API ready (`POST /auth/guest`)
- ✅ Frontend implemented (Try Demo button + Guest Banner)
- ✅ Pushed to GitHub
- ⏳ **Pending**: Database migration
- ⏳ **Pending**: Frontend deployment to Vercel
- ⏳ **Pending**: Cleanup cron job setup

## Deployment Checklist

- [ ] Run database migration (add `is_guest` column)
- [ ] Deploy frontend to Vercel
- [ ] Test guest account creation
- [ ] Test document upload as guest
- [ ] Test data isolation (create 2 guests)
- [ ] Setup cleanup cron job
- [ ] Test cleanup script
- [ ] Monitor guest → permanent conversion rate

---

**Your Try Demo feature is complete! Users can now instantly try your RAG assistant without any signup friction.** 🎉
