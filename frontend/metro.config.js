const { getDefaultConfig } = require("expo/metro-config");
const { createApiProxy } = require("./dev-proxy");

const config = getDefaultConfig(__dirname);

// Puerto del backend (por defecto 8000, el de run.py).
const apiProxy = createApiProxy({
  prefix: "/api/",
  host: "127.0.0.1",
  port: Number(process.env.BACKEND_PORT) || 8000,
});

const previous = config.server && config.server.enhanceMiddleware;
config.server = {
  ...config.server,
  enhanceMiddleware: (middleware, server) => {
    const base = previous ? previous(middleware, server) : middleware;
    return (req, res, next) => apiProxy(req, res, () => base(req, res, next));
  },
};

module.exports = config;
