# CPC Detection Report System - Deployment Package

## Quick Start

This is a static web application for CPC (China Petroleum Corporation) safety violation detection and review system.

### Deployment Options

**Option 1: Static Web Server**
```bash
# Upload to your web server
scp -r deployment_package/ user@server:/var/www/cpc-detection/

# Serve with Nginx/Apache
# Entry point: index.html
```

**Option 2: Cloud Storage (S3/GCS/Azure)**
```bash
# AWS S3 example
aws s3 sync deployment_package/ s3://your-bucket/ --acl public-read

# Enable static website hosting in S3 settings
```

### Requirements

- HTTPS enabled (required for API calls)
- Access to API endpoints:
  - `https://apigatewayiseek.intemotech.com/vision_logic/video`
  - `https://apigatewayiseek.intemotech.com/vision_logic/logs/notify/image`
  - `https://apigatewayiseek.intemotech.com/vision_logic/logs/notify/filter`

### File Structure

```
deployment_package/
├── index.html           # Main entry page (report list)
├── 2026/                # Data directory (organized by date)
│   ├── 03/30/          # March 30, 2026
│   ├── 03/31/          # March 31, 2026
│   ├── 04/01/          # April 1, 2026
│   ├── 04/02/          # April 2, 2026
│   └── 04/07/          # April 7, 2026
├── scripts/             # Maintenance scripts (optional)
│   ├── generate_daily_review.py
│   └── regenerate_0407_merged.py
├── 部署說明.md          # Deployment guide (Chinese)
└── README.md            # This file
```

### How It Works

1. **index.html** - Main dashboard showing all available reports
2. **審核.html** - Review page for violations (approve/reject)
3. **報告_管理版.html** - Final report (approved violations only)
4. **Data Flow**: API → Review → localStorage → Report

### Configuration

All data is embedded in HTML files. To add new dates:

1. Create new directory: `2026/MM/DD/`
2. Add HTML files for review and report
3. Update `REPORT_DATA` array in `index.html`:

```javascript
const REPORT_DATA = [
  {
    "date": "2026-04-08",
    "category": "高處作業",  // or "局限空間"
    "reviewPath": "2026/04/08/高處作業_審核.html",
    "reportPath": "2026/04/08/高處作業_報告_管理版.html"
  }
];
```

### Support

For detailed deployment instructions, see `部署說明.md` (Chinese documentation).

---

**Version**: 1.0
**Last Updated**: 2026-04-08
**Tech Stack**: Pure HTML/CSS/JavaScript (no build required)
