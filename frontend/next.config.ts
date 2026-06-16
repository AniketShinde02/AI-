const path = require('path');

const nextConfig = {
  outputFileTracingRoot: path.join(__dirname, '../../'),
  webpack: (config: any) => {
    config.resolve.modules = [
      path.resolve(__dirname, 'node_modules'),
      'node_modules'
    ];
    return config;
  },
  turbopack: {},
};

module.exports = nextConfig;

