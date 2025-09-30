# BRANE Landing Page

A stunning, modern landing page for BRANE - privacy-first AI orchestration platform.

## Features

- **Responsive Design**: Mobile-first, works across all devices
- **Dark Mode**: Professional dark theme optimized for healthcare professionals
- **Glassmorphism**: Modern UI with glass effects and gradients
- **Privacy Tier Visualization**: Clear distinction between Tier 0, 1, and 2 privacy levels
- **Interactive Elements**: Tabs, modals, smooth scrolling, and animations
- **Performance Optimized**: Pure HTML/CSS/JS with Tailwind CSS via CDN
- **SEO Ready**: Semantic HTML with proper meta tags
- **Accessibility**: WCAG compliant with keyboard navigation

## Structure

```
landing/
├── index.html              # Main landing page
├── assets/
│   ├── css/
│   │   └── styles.css     # Custom animations and styles
│   ├── js/
│   │   └── main.js        # Interactions and animations
│   └── images/
│       └── logo.svg       # BRANE logo
└── README.md              # This file
```

## Deployment

### Automatic Deployment (GitHub Pages)

The landing page automatically deploys to GitHub Pages on every push to `main` that affects the `landing/` directory.

1. **Enable GitHub Pages**:
   - Go to repository Settings > Pages
   - Source: "GitHub Actions"
   - The workflow will handle the rest

2. **Workflow**: `.github/workflows/deploy-landing.yml`
   - Triggers on push to main (landing/* changes)
   - Deploys to GitHub Pages
   - Runs health check

### Manual Deployment

1. **Static Hosting** (Netlify, Vercel, etc.):
   ```bash
   # Deploy the landing/ folder to your host
   netlify deploy --dir=landing --prod
   ```

2. **Local Development**:
   ```bash
   # Simple HTTP server
   cd landing
   python3 -m http.server 8000
   # Open http://localhost:8000
   ```

## Customization

### Colors

Edit Tailwind config in `index.html` (line 22-34):

```javascript
theme: {
    extend: {
        colors: {
            primary: '#0066FF',      // Primary blue
            'tier-0': '#10B981',     // Green (local)
            'tier-1': '#F59E0B',     // Amber (encrypted cloud)
            'tier-2': '#EF4444',     // Red (public API)
            background: '#0A0A0A',   // Dark background
        }
    }
}
```

### Content

Key sections to update:

1. **Hero Section** (line 53):
   - Headline, subheadline, CTA buttons

2. **Privacy Tiers** (line 168):
   - Tier descriptions and features

3. **Key Features** (line 281):
   - Feature cards

4. **Pricing** (line 520):
   - Pricing tiers and features

5. **Footer** (line 716):
   - Links and company info

### Logo

Replace `/Users/sharminsirajudeen/Projects/brane_v2/landing/assets/images/logo.svg` with your own logo.

## Performance

- **No build step**: Pure HTML/CSS/JS
- **CDN assets**: Tailwind CSS via CDN
- **Optimized animations**: CSS-based with GPU acceleration
- **Lazy loading**: Images and assets loaded on demand
- **Minimal JS**: ~200 lines of vanilla JavaScript

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari, Chrome Android)

## Analytics

To add analytics, insert your tracking code in `index.html` before `</body>`:

```html
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=YOUR-ID"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'YOUR-ID');
</script>
```

## License

Copyright 2025 BRANE. All rights reserved.

## Support

For questions or issues:
- GitHub: https://github.com/brane-ai/brane
- Email: contact@brane.ai
- Docs: https://docs.brane.ai
