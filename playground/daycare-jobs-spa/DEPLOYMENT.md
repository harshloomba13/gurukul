# Deployment Guide

## Quick Deploy Options

### Option 1: Vercel (Recommended - Easiest) ⚡

1. **Install Vercel CLI** (if not installed):
   ```bash
   npm install -g vercel
   ```

2. **Deploy**:
   ```bash
   cd playground/daycare-jobs-spa
   vercel
   ```
   
   Follow the prompts:
   - Link to existing project? **No** (first time)
   - Project name: `daycare-jobs-spa` (or your choice)
   - Directory: `./` (current directory)
   - Override settings? **No**

3. **Or deploy via GitHub**:
   - Go to https://vercel.com/new
   - Import your GitHub repository: `harshloomba13/gurukul`
   - Root Directory: `playground/daycare-jobs-spa`
   - Framework Preset: **Create React App**
   - Build Command: `npm run build`
   - Output Directory: `build`
   - Click **Deploy**

### Option 2: Netlify 🌐

1. **Install Netlify CLI**:
   ```bash
   npm install -g netlify-cli
   ```

2. **Deploy**:
   ```bash
   cd playground/daycare-jobs-spa
   netlify deploy --prod
   ```

3. **Or deploy via GitHub**:
   - Go to https://app.netlify.com
   - Click "New site from Git"
   - Connect GitHub and select `gurukul` repository
   - Base directory: `playground/daycare-jobs-spa`
   - Build command: `npm run build`
   - Publish directory: `build`
   - Click "Deploy site"

### Option 3: Render 🚀

1. Go to https://render.com
2. Click "New +" → "Static Site"
3. Connect your GitHub repository: `harshloomba13/gurukul`
4. Settings:
   - **Name**: `daycare-jobs-spa`
   - **Root Directory**: `playground/daycare-jobs-spa`
   - **Build Command**: `npm install && npm run build`
   - **Publish Directory**: `build`
5. Click "Create Static Site"

### Option 4: GitHub Pages 📄

1. Update `package.json` homepage:
   ```json
   "homepage": "https://harshloomba13.github.io/daycare-jobs-spa"
   ```

2. Install gh-pages:
   ```bash
   npm install --save-dev gh-pages
   ```

3. Add to package.json scripts:
   ```json
   "scripts": {
     "predeploy": "npm run build",
     "deploy": "gh-pages -d build"
   }
   ```

4. Deploy:
   ```bash
   npm run deploy
   ```

## Post-Deployment

After deployment, your app will be live at:
- **Vercel**: `https://daycare-jobs-spa.vercel.app` (or custom domain)
- **Netlify**: `https://daycare-jobs-spa.netlify.app` (or custom domain)
- **Render**: `https://daycare-jobs-spa.onrender.com` (or custom domain)

## Environment Variables

Currently, the app uses client-side only storage. If you need backend integration later, add environment variables in your deployment platform's dashboard.

