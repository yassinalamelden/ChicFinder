const { getDefaultConfig } = require("expo/metro-config");

const config = getDefaultConfig(__dirname);

// The Firebase JS SDK ships .cjs entry points that Metro's default resolver
// does not pick up, which surfaces as "Component auth has not been registered".
config.resolver.sourceExts = [...config.resolver.sourceExts, "cjs"];
config.resolver.unstable_enablePackageExports = false;

module.exports = config;
