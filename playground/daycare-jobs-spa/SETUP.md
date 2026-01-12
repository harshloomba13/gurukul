# Quick Setup Guide

## Installation Steps

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Start the development server:**
   ```bash
   npm start
   ```

3. **Open your browser:**
   Navigate to `http://localhost:3000`

## First Time Usage

1. **Login Page**: You'll see the login page first
2. **Sign In Options**:
   - Enter your name/email and click "Sign in" (as Teacher or Guest)
   - Or click "Continue as guest" for quick access
3. **Dashboard**: After login, you'll see the job listings dashboard

## Features to Try

- **Search**: Type in the search box to find specific daycares or roles
- **Region Tabs**: Click on region tabs (Vancouver, Surrey, etc.) to filter jobs
- **Filters**: Use dropdowns to filter by region or job type
- **Logout**: Click logout to clear your session

## Analytics Data

All user events are stored in browser localStorage under the key `carelink-analytics`. You can access this data via browser console:

```javascript
JSON.parse(localStorage.getItem('carelink-analytics'))
```

This data can be exported or sent to an analytics service for monetization tracking.

## Building for Production

```bash
npm run build
```

This creates an optimized production build in the `build` folder.

