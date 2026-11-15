@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo [1/3] Pulling latest changes from GitHub...
git pull origin main --no-edit
echo [2/3] Running Local Dubizzle Owner Scraper...
python -u scraper.py
echo [3/3] Pushing updated ads.json to GitHub and Vercel...
git add ads.json seen_links.json
git commit -m "Local Residential IP Update: Verified Dubizzle Owners Only"
git push origin main
echo Done!
