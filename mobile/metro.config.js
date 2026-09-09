const { getDefaultConfig } = require("expo/metro-config");

const config = getDefaultConfig(__dirname);

// Package exports must stay ENABLED. The Firebase SDK ships a "react-native"
// export condition (@firebase/auth -> dist/rn/index.js) and that build is the
// only one exporting getReactNativePersistence. Disabling package exports makes
// Metro fall back to the legacy `main`/`browser` fields, which resolve the WEB
// build instead: getReactNativePersistence comes back undefined, auth silently
// loses persistence, and the failure surfaces later as a confusing
// auth/invalid-api-key. Do not set unstable_enablePackageExports = false here.

module.exports = config;
