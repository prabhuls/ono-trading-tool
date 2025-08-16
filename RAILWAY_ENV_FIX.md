# Railway Environment Variables Fix

## The Problem
Next.js `NEXT_PUBLIC_*` variables are embedded at **BUILD TIME**, not runtime. When Railway builds the Docker image, it needs access to these variables DURING the build.

## The Solution

### 1. Set Environment Variables in Railway
In your Railway frontend service, ensure you have:
```
NEXT_PUBLIC_BACKEND_URL=https://your-backend-service.railway.app
```

### 2. Railway Auto-Injection
Railway automatically passes ALL environment variables as Docker build arguments. Our updated Dockerfile now:
- Accepts these as ARG
- Sets them as ENV
- Uses them during `npm run build`

### 3. How It Works
```dockerfile
# These lines in Dockerfile:
ARG NEXT_PUBLIC_BACKEND_URL
ENV NEXT_PUBLIC_BACKEND_URL=$NEXT_PUBLIC_BACKEND_URL
```

This ensures the variable is available when Next.js builds and bakes it into the client-side code.

### 4. Verification
After deployment, check the Railway build logs for:
```
Building with NEXT_PUBLIC_BACKEND_URL=https://your-backend.railway.app
```

If you see your actual URL there, it's working!

## Important Notes
- Changes to environment variables require a REBUILD, not just a restart
- Use Railway's "Redeploy" button after changing environment variables
- The variables must be set BEFORE the build starts

## Alternative Approach (if needed)
If the above doesn't work, you can:
1. Fork the deployment
2. Hard-code the backend URL in next.config.mjs temporarily
3. Use a runtime configuration approach with window variables