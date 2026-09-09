module.exports = function (api) {
  api.cache(true);
  return {
    // babel-preset-expo already wires up the Reanimated/Worklets plugin when
    // those packages are installed, so no extra plugin entry is needed here.
    presets: ["babel-preset-expo"],
  };
};
