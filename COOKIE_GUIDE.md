# How to Get Complete Cookies for nhentai

## Current Status

✅ **Cloudflare Bypass: WORKING**
The app successfully bypasses Cloudflare protection using curl_cffi.

⚠️ **Authentication: Requires Full Cookies**
The `cf_clearance` cookie only bypasses Cloudflare's anti-bot challenge. To access authenticated features like favorites, you need ALL session cookies.

## How to Get All Cookies (Firefox)

1. **Log in to nhentai.net** in your Firefox browser

2. **Open Developer Tools** (F12)

3. **Go to the Network tab**

4. **Refresh the page** (F5)

5. **Click on any request** to nhentai.net

6. **Go to the "Cookies" tab** in the request details

7. **Copy ALL cookie values** - you'll see multiple cookies like:
   - `cf_clearance` (Cloudflare bypass)
   - `sessionid` (your login session)
   - `csrftoken` (CSRF protection)
   - And possibly others

8. **Format them as a single cookie string** separated by semicolons:
   ```
   cf_clearance=VALUE1; sessionid=VALUE2; csrftoken=VALUE3
   ```

9. **Set the complete cookie string**:
   ```bash
   nhentai --cookie "cf_clearance=VALUE1; sessionid=VALUE2; csrftoken=VALUE3"
   ```

## Alternative: Copy from Headers Tab

1. In Developer Tools Network tab, click on a request
2. Go to the **Headers** tab
3. Scroll to **Request Headers**
4. Find the **Cookie** header
5. Copy the ENTIRE value (all cookies together)
6. Use that value with `nhentai --cookie "..."`

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
