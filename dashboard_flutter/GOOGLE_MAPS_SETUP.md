# Google Maps Setup Guide

## Current Status
✅ **API Key Added**: `AIzaSyBTFnwEECdU8R0bACR-OhdTIrq33Nd2-CI`  
⚠️ **Issue**: "For development purposes only" watermark  
⚠️ **Issue**: Map styling not applied properly  

## Steps to Remove "For Development Purposes Only" Watermark

### 1. Enable Billing on Google Cloud Project
The watermark appears primarily because **billing is not enabled**. This is the most common cause.

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project (or create a new one)
3. Navigate to **Billing** → **Link a billing account**
4. Add a valid payment method (Google provides $200 free credits for new accounts)

### 2. Enable Required APIs
Enable these APIs in the [Google Cloud Console](https://console.cloud.google.com/apis/library):

- ✅ **Maps JavaScript API** (required for web maps)
- ✅ **Places API** (for place search functionality)
- ✅ **Geocoding API** (for address/coordinate conversion)
- ✅ **Directions API** (if you plan to show routes)

### 3. Configure API Key Restrictions (Recommended)
In [Google Cloud Console](https://console.cloud.google.com/apis/credentials):

1. Click on your API key
2. Under **Application restrictions**:
   - Select **HTTP referrers (web sites)**
   - Add: `localhost:*/*` (for development)
   - Add: `yourdomain.com/*` (for production)

3. Under **API restrictions**:
   - Select **Restrict key**
   - Choose: Maps JavaScript API, Places API, Geocoding API

### 4. Check API Key Quotas
1. Go to **APIs & Services** → **Quotas**
2. Ensure your quotas are sufficient:
   - Maps JavaScript API: 25,000 map loads per day (free tier)
   - Places API: $17 per 1000 requests after free tier

## Testing the Setup

After completing the above steps:

1. **Restart your Flutter app**:
   ```bash
   cd dashboard_flutter
   flutter run -d web-server --web-port 8082
   ```

2. **Check the browser console** for any API errors
3. **The watermark should disappear** within a few minutes

## Troubleshooting

### If watermark persists:
1. **Wait 5-10 minutes** - Changes can take time to propagate
2. **Clear browser cache** - Hard refresh (Cmd+Shift+R on Mac, Ctrl+Shift+R on Windows)
3. **Verify billing is active** - Check Google Cloud Console billing section
4. **Check quotas** - Ensure you haven't exceeded free tier limits

### Common Error Messages:
- `"This API project is not authorized to use this API"` → Enable the required APIs
- `"API key not found"` → Check the API key in `web/index.html`
- `"REQUEST_DENIED"` → Check API key restrictions and billing

## Current Implementation Features

✅ **Interactive Google Maps** with custom Apple-style theming  
✅ **Drag & Drop** markers to move intersections  
✅ **Click to Create** new intersections in edit mode  
✅ **Real-time Updates** with intersection status indicators  
✅ **Responsive Design** for mobile and desktop  
✅ **Dark/Light Theme** support with appropriate map styling  

## Map Styling
The app automatically applies custom styling that matches your Apple design system:
- **Light Theme**: Clean white roads, soft blue water, minimal colors
- **Dark Theme**: Dark gray base, muted colors, iOS-style dark mode appearance

## Next Steps
1. ✅ Complete the billing setup in Google Cloud Console
2. ✅ Refresh the app and check for watermark removal
3. ✅ Test drag & drop functionality in edit mode
4. ✅ Test click-to-create new intersections

The interactive map is now fully functional - once billing is enabled, you'll have a professional-grade mapping experience with no development watermarks! 