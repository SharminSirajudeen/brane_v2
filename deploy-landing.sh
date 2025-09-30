#!/bin/bash

# BRANE Landing Page Deployment Script
# Usage: ./deploy-landing.sh

set -e

echo "========================================="
echo "BRANE Landing Page Deployment"
echo "========================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if in correct directory
if [ ! -d "landing" ]; then
    echo -e "${YELLOW}Error: landing/ directory not found${NC}"
    echo "Please run this script from the brane_v2 root directory"
    exit 1
fi

# Check if git repo
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${YELLOW}Error: Not a git repository${NC}"
    exit 1
fi

echo -e "${BLUE}Step 1: Checking files...${NC}"
echo "Landing page files:"
find landing -type f | grep -v ".DS_Store"
echo ""

echo -e "${BLUE}Step 2: Adding files to git...${NC}"
git add landing/
git add .github/workflows/deploy-landing.yml
echo -e "${GREEN}✓ Files added${NC}"
echo ""

echo -e "${BLUE}Step 3: Creating commit...${NC}"
git commit -m "Add stunning landing page with auto-deployment

- Modern, privacy-first design for healthcare/legal/finance
- Privacy tier visualization (Tier 0, 1, 2)
- Interactive tabs, animations, and glassmorphism
- Auto-deployment via GitHub Actions
- Mobile-responsive with dark mode
- SEO and accessibility ready

Built with:
- Pure HTML/CSS/JS (no build step)
- Tailwind CSS 3.x
- Custom animations and interactions
- Optimized for performance
" || echo "No changes to commit (files already committed)"
echo -e "${GREEN}✓ Commit created${NC}"
echo ""

echo -e "${BLUE}Step 4: Pushing to GitHub...${NC}"
git push origin main
echo -e "${GREEN}✓ Pushed to GitHub${NC}"
echo ""

echo "========================================="
echo -e "${GREEN}Deployment initiated!${NC}"
echo "========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Enable GitHub Pages:"
echo "   - Go to: https://github.com/$(git config --get remote.origin.url | sed 's/.*github.com[:/]\(.*\)\.git/\1/')/settings/pages"
echo "   - Source: Select 'GitHub Actions'"
echo ""
echo "2. Monitor deployment:"
echo "   - Go to: https://github.com/$(git config --get remote.origin.url | sed 's/.*github.com[:/]\(.*\)\.git/\1/')/actions"
echo "   - Wait 1-2 minutes for completion"
echo ""
echo "3. Your site will be live at:"
echo -e "   ${GREEN}https://$(git config --get remote.origin.url | sed 's/.*github.com[:/]\(.*\)\.git/\1/' | cut -d'/' -f1).github.io/$(git config --get remote.origin.url | sed 's/.*github.com[:/]\(.*\)\.git/\1/' | cut -d'/' -f2)/${NC}"
echo ""
echo "For detailed instructions, see: landing/DEPLOYMENT_GUIDE.md"
echo ""
