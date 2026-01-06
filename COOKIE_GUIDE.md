# How to Get Complete Cookies for nhentai

## Current Status

✅ **Cloudflare Bypass: WORKING**
The app successfully bypasses Cloudflare protection using curl_cffi.

⚠️ **Authentication: Requires Full Cookies**
The `cf_clearance` cookie only bypasses Cloudflare's anti-bot challenge. To access authenticated features like favorites, you need ALL session cookies.

## Method 1: Storage/Application Tab (RECOMMENDED)

This is the most reliable method because it shows all cookies directly.

### Firefox:

1. **Log in to nhentai.net** in Firefox
2. **Open Developer Tools** (F12)
3. **Go to the Storage tab**
4. **Expand Cookies** in the left sidebar
5. **Click on https://nhentai.net**
6. You'll see a table with all cookies:
   - `cf_clearance` (Cloudflare bypass)
   - `sessionid` (your login session)
   - `csrftoken` (CSRF protection)
   - `session-affinity` (load balancer session)
7. **Manually copy each Value** and format as:
   ```
   cf_clearance=VALUE1;sessionid=VALUE2;csrftoken=VALUE3;session-affinity=VALUE4
   ```
8. **Set the complete cookie string**:
   ```bash
   nhentai --cookie="cf_clearance=VALUE1;sessionid=VALUE2;csrftoken=VALUE3;session-affinity=VALUE4"
   ```

### Chrome:

1. **Log in to nhentai.net** in Chrome
2. **Open Developer Tools** (F12)
3. **Go to the Application tab** (top bar)
4. **Expand Storage → Cookies** in the left sidebar
5. **Click on https://nhentai.net**
6. You'll see a table with all cookies
7. **Copy each Value** and format as shown above

## Method 2: Network Tab (Alternative)

**⚠️ IMPORTANT**: You must look at requests to **nhentai.net** (the main site), NOT image requests!

Image requests (to `t4.nhentai.net`, `i1.nhentai.net`, etc.) only include `cf_clearance`, not your session cookies.

### Steps:

1. **Open Developer Tools** (F12) → Network tab
2. **Refresh the page** (F5)
3. **Look for the FIRST request** - it should be to `nhentai.net` (the main document)
   - ❌ NOT requests to `t4.nhentai.net/galleries/...` (these are images)
   - ✅ YES requests to just `nhentai.net` or `nhentai.net/` (the main page)
4. **Click on that request**
5. **Go to the Headers tab**
6. **Scroll to Request Headers**
7. **Find the Cookie header** - it should show ALL cookies
8. **Copy the ENTIRE value**
9. Use that value with `nhentai --cookie="..."`

## Testing Your Cookies

After setting your cookies, run:
```bash
nhentai --search "test" --page 1
```

If you see:
- ✅ `Login successfully! Your username: YourName` - Full authentication working!
- ⚠️ `Cloudflare bypass successful, but not logged in` - Need more cookies

## Cookie Expiration

Note: Cookies expire after some time. If downloads stop working, you'll need to:
1. Log in to nhentai.net again in your browser
2. Get fresh cookies using the steps above
3. Set them again with `nhentai --cookie`

## What Each Cookie Does

- **cf_clearance**: Bypasses Cloudflare's anti-bot protection (required)
- **sessionid**: Maintains your login session (required for favorites)
- **csrftoken**: Security token for form submissions (required for favorites)
- **session-affinity**: Load balancer session tracking (required for some features)

## Why Image Requests Don't Show All Cookies

When you look at the Network tab, you might notice:

```
Request to nhentai.net:
Cookie: cf_clearance=...; sessionid=...; csrftoken=...; session-affinity=...

Request to t4.nhentai.net (images):
Cookie: cf_clearance=...
```

**This is normal!** Cookies are domain-specific for security:

- Session cookies (`sessionid`, `csrftoken`) are set for `nhentai.net` domain
- They are **NOT** sent to subdomains like `t4.nhentai.net`, `i1.nhentai.net`
- Only `cf_clearance` is set for `*.nhentai.net` (all subdomains)

**That's why**: Always check the **Storage tab** or requests to the **main nhentai.net domain** to see all cookies!
