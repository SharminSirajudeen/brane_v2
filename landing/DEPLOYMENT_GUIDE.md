# BRANE Landing Page - Deployment Guide

## Quick Start (3 Steps)

### Step 1: Commit and Push the Landing Page

```bash
cd /Users/sharminsirajudeen/Projects/brane_v2

# Add all landing page files
git add landing/
git add .github/workflows/deploy-landing.yml

# Commit
git commit -m "Add stunning landing page with auto-deployment

- Modern, privacy-first design for healthcare/legal/finance
- Privacy tier visualization (Tier 0, 1, 2)
- Interactive tabs, animations, and glassmorphism
- Auto-deployment via GitHub Actions
- Mobile-responsive with dark mode
- SEO and accessibility ready"

# Push to GitHub
git push origin main
```

### Step 2: Enable GitHub Pages

1. Go to your repository on GitHub
2. Click **Settings** tab
3. Scroll down to **Pages** in the left sidebar
4. Under **Build and deployment**:
   - **Source**: Select "GitHub Actions"
   - That's it! No need to select a branch.

### Step 3: Wait for Deployment

1. Go to **Actions** tab in your repository
2. You should see "Deploy Landing Page to GitHub Pages" workflow running
3. Wait 1-2 minutes for completion
4. Your site will be live at: `https://YOUR-USERNAME.github.io/brane_v2/`

## Deployment Options

### Option A: GitHub Pages (Recommended)

**Pros**:
- Free hosting
- Automatic SSL
- Auto-deployment on every push
- CDN-backed

**Setup**: Follow Quick Start above

**URL**: `https://YOUR-USERNAME.github.io/brane_v2/`

### Option B: Custom Domain (GitHub Pages)

1. Buy a domain (e.g., `brane.ai`)

2. Add CNAME file:
   ```bash
   echo "brane.ai" > landing/CNAME
   git add landing/CNAME
   git commit -m "Add custom domain"
   git push
   ```

3. Configure DNS:
   - Add A records pointing to GitHub:
     - `185.199.108.153`
     - `185.199.109.153`
     - `185.199.110.153`
     - `185.199.111.153`

4. In GitHub Settings > Pages:
   - Enter custom domain: `brane.ai`
   - Check "Enforce HTTPS"

**URL**: `https://brane.ai`

### Option C: Netlify

**Pros**:
- Fastest deployment
- Better analytics
- Form handling
- Instant rollbacks

**Setup**:
```bash
# Install Netlify CLI
npm install -g netlify-cli

# Login
netlify login

# Deploy
cd landing
netlify deploy --prod

# Or link to Git for auto-deploy
netlify init
```

**URL**: `https://YOUR-SITE.netlify.app` or custom domain

### Option D: Vercel

**Pros**:
- Edge network
- Analytics
- Preview deployments

**Setup**:
```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
cd landing
vercel --prod

# Or connect via GitHub integration
```

**URL**: `https://YOUR-SITE.vercel.app` or custom domain

### Option E: AWS S3 + CloudFront

**Pros**:
- Full control
- Scalable
- Professional setup

**Setup**:
```bash
# Install AWS CLI
brew install awscli

# Configure
aws configure

# Create S3 bucket
aws s3 mb s3://brane-landing

# Enable static website hosting
aws s3 website s3://brane-landing --index-document index.html

# Upload files
cd landing
aws s3 sync . s3://brane-landing --acl public-read

# Create CloudFront distribution
# (Use AWS Console for this)
```

**URL**: Your CloudFront URL or custom domain

## Testing Locally

```bash
cd /Users/sharminsirajudeen/Projects/brane_v2/landing

# Option 1: Python
python3 -m http.server 8000

# Option 2: Node.js
npx serve .

# Option 3: PHP
php -S localhost:8000

# Open: http://localhost:8000
```

## Continuous Deployment

The GitHub Actions workflow automatically:

1. **Triggers** on:
   - Push to `main` branch
   - Changes in `landing/` directory
   - Manual workflow dispatch

2. **Steps**:
   - Checkout code
   - Setup GitHub Pages
   - Upload landing page artifact
   - Deploy to GitHub Pages
   - Run health check

3. **Workflow file**: `.github/workflows/deploy-landing.yml`

## Troubleshooting

### Issue: GitHub Pages not showing

**Solutions**:
1. Check Actions tab for errors
2. Ensure GitHub Pages source is "GitHub Actions"
3. Wait 2-3 minutes after first deployment
4. Clear browser cache

### Issue: CSS not loading

**Solutions**:
1. Check file paths are relative
2. Ensure Tailwind CDN is accessible
3. Check browser console for errors

### Issue: 404 on deployment

**Solutions**:
1. Verify `landing/index.html` exists
2. Check workflow logs in Actions tab
3. Ensure repository is public (or GitHub Pro for private)

### Issue: Animations not working

**Solutions**:
1. Check JavaScript console for errors
2. Ensure `assets/js/main.js` is loaded
3. Verify browser supports modern JavaScript

## Performance Optimization

### 1. Enable Compression

For custom servers, enable gzip/brotli:

**Nginx**:
```nginx
gzip on;
gzip_types text/css application/javascript image/svg+xml;
```

**Apache**:
```apache
AddOutputFilterByType DEFLATE text/html text/css application/javascript
```

### 2. CDN (Already using Tailwind CDN)

Landing page already uses:
- Google Fonts CDN
- Tailwind CSS CDN

### 3. Caching

Add cache headers:

```nginx
location ~* \.(css|js|svg)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

### 4. Image Optimization

```bash
# Install tools
brew install imagemagick

# Optimize images
cd landing/assets/images
for img in *.png *.jpg; do
    convert "$img" -strip -quality 85 "$img"
done
```

## Analytics Integration

### Google Analytics

Add before `</body>` in `index.html`:

```html
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-XXXXXXXXXX');
</script>
```

### Plausible (Privacy-friendly)

```html
<script defer data-domain="brane.ai" src="https://plausible.io/js/script.js"></script>
```

## Security

### Content Security Policy

Add to `index.html` `<head>`:

```html
<meta http-equiv="Content-Security-Policy" content="
    default-src 'self';
    script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://fonts.googleapis.com;
    style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
    font-src 'self' https://fonts.gstatic.com;
    img-src 'self' data:;
    connect-src 'self';
">
```

### HTTPS

All deployment options above provide HTTPS by default.

## Monitoring

### Uptime Monitoring

Use services like:
- UptimeRobot (free)
- Pingdom
- StatusCake

### Performance Monitoring

Use:
- Google Lighthouse
- WebPageTest
- GTmetrix

```bash
# Run Lighthouse
npx lighthouse https://YOUR-SITE.github.io/brane_v2/ --view
```

## Next Steps

1. **Deploy now**: Follow Quick Start above
2. **Custom domain**: Set up custom domain
3. **Analytics**: Add tracking
4. **SEO**: Submit sitemap to Google Search Console
5. **Social**: Share on Twitter, LinkedIn, Product Hunt

## Support

If you encounter issues:
1. Check Actions tab for deployment logs
2. Review browser console for errors
3. Ensure all files are committed
4. Verify GitHub Pages is enabled

## Live URL

After deployment, your landing page will be at:

**GitHub Pages**: `https://YOUR-USERNAME.github.io/brane_v2/`

Replace `YOUR-USERNAME` with your actual GitHub username.

---

**Ready to deploy?** Run the commands in Step 1 above!
