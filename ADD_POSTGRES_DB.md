# How to Add PostgreSQL Database to Railway Project

## Step-by-Step Instructions

### Step 1: Open Your Railway Project

1. Go to [Railway Dashboard](https://railway.app/dashboard)
2. Click on your project (the one containing your Flask app)

### Step 2: Add PostgreSQL Database Service

1. In your project dashboard, click the **"New"** button (usually a **+** or **"New Service"** button)
2. From the dropdown menu, select **"Database"**
3. Choose **"Add PostgreSQL"** from the database options

### Step 3: Railway Automatically Configures Everything

Once you add PostgreSQL, Railway will:

- ✅ Create a new PostgreSQL database service
- ✅ Automatically generate connection credentials
- ✅ **Automatically set the `DATABASE_URL` environment variable** for your web service
- ✅ Link the database to your web service (if they're in the same project)

### Step 4: Verify the Connection

#### Option A: Check Environment Variables

1. Click on your **web service** (your Flask app)
2. Go to the **"Variables"** tab
3. Look for `DATABASE_URL` - it should be automatically set
4. The URL will look like: `postgres://postgres:password@hostname:port/railway`

#### Option B: Check Service Connections

1. In your project dashboard, you should see two services:
   - Your web service (Flask app)
   - PostgreSQL service
2. They should be automatically connected (you'll see a connection line between them)

### Step 5: Verify Database is Working

After your app redeploys (Railway will automatically redeploy when `DATABASE_URL` is set):

1. Check the **Logs** tab of your web service
2. Look for successful database connection messages
3. Your app should automatically create the tables on first run (via `db.create_all()` in `app.py`)

## How It Works

Your Flask app is already configured to:

1. **Read `DATABASE_URL`** from environment variables (line 15 in `app.py`)
2. **Convert Railway's format** from `postgres://` to `postgresql://` (lines 16-17 in `app.py`)
3. **Use PostgreSQL** if `DATABASE_URL` is set, otherwise fall back to SQLite

```python
# From app.py
database_url = os.environ.get('DATABASE_URL') or 'sqlite:///face_recognition.db'
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
```

## Manual Linking (If Needed)

If Railway doesn't automatically link the services:

1. Click on your **web service**
2. Go to **"Settings"** tab
3. Scroll to **"Service Connections"** or **"Variables"**
4. You should see `DATABASE_URL` listed - if not, Railway should add it automatically
5. If you need to manually add it:
   - Go to PostgreSQL service → **"Variables"** tab
   - Copy the `DATABASE_URL` value
   - Go to web service → **"Variables"** tab
   - Click **"New Variable"**
   - Name: `DATABASE_URL`
   - Value: Paste the connection string
   - Click **"Add"**

## Troubleshooting

### Database URL Not Appearing

- **Wait a moment**: Railway may take a few seconds to set the variable
- **Refresh the page**: Sometimes the UI needs a refresh
- **Check both services**: Make sure both web and PostgreSQL services are in the same project

### Connection Errors

If you see database connection errors in logs:

1. **Verify `DATABASE_URL` is set**:
   - Go to web service → Variables tab
   - Confirm `DATABASE_URL` exists and has a value

2. **Check the URL format**:
   - Should start with `postgres://` (Railway format)
   - Your app converts it to `postgresql://` automatically

3. **Verify PostgreSQL service is running**:
   - Check the PostgreSQL service status (should be green/running)
   - Check PostgreSQL service logs for any errors

4. **Check app logs**:
   - Look for SQLAlchemy connection errors
   - Verify the app is reading the environment variable correctly

### Database Tables Not Created

Your app creates tables automatically on startup via `db.create_all()` in `app.py` (line 117).

If tables aren't created:

1. **Check app startup logs** for errors
2. **Verify database connection** is successful
3. **Manually trigger table creation** by restarting the service:
   - Go to web service → Settings → Restart

## Viewing Your Database

### Using Railway Dashboard

1. Click on your **PostgreSQL service**
2. Go to **"Data"** or **"Query"** tab (if available)
3. You can view tables and run queries

### Using External Tools

1. Get connection details from PostgreSQL service → **"Variables"** tab
2. Use tools like:
   - **pgAdmin**
   - **DBeaver**
   - **TablePlus**
   - **psql** (command line)

Connection details are in the `DATABASE_URL`:
- Format: `postgres://username:password@hostname:port/database`
- Extract each component for your database client

## Next Steps

After adding PostgreSQL:

1. ✅ **Verify connection** - Check logs for successful connection
2. ✅ **Test your app** - Register a student and verify data persists
3. ✅ **Set up backups** - Consider Railway's backup options or external backups
4. ✅ **Monitor usage** - Keep an eye on database size and connections

## Important Notes

- **Data Persistence**: PostgreSQL data persists across deployments (unlike SQLite)
- **Automatic Backups**: Railway may provide automatic backups depending on your plan
- **Connection Limits**: PostgreSQL has connection limits - your app uses connection pooling via SQLAlchemy
- **Cost**: PostgreSQL service may incur additional costs depending on your Railway plan

## Summary

Adding PostgreSQL is simple:
1. Click **"New"** → **"Database"** → **"Add PostgreSQL"**
2. Railway automatically sets `DATABASE_URL`
3. Your app automatically uses it
4. Done! ✅

No manual configuration needed - Railway handles everything automatically!

