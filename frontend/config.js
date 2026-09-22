/**
 * Frontend Runtime Configuration & Environment Resolver
 * Dynamically switches between local development and your deployed Render backend.
 */
const CONFIG = {
  API_BASE_URL: (() => {
    const isLocalhost = Boolean(
      window.location.hostname === "localhost" ||
      window.location.hostname === "127.0.0.1" ||
      window.location.hostname === "[::1]"
    );

    // Local development endpoint
    if (isLocalhost) {
      return "http://127.0.0.1:8000/api";
    }

    // Live Render production backend URL
    // Replace with your actual Render service name if different
    return "https://student-verification-backend.onrender.com/api";
  })()
};

// Freeze the object to prevent accidental runtime modifications
Object.freeze(CONFIG);
