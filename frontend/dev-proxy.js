
const http = require("http");

function createApiProxy({ prefix = "/api/", host = "127.0.0.1"} = {}) {
  return function apiProxy(req, res, next) {
    if (!req.url.startsWith(prefix)) return next();

    const proxyReq = http.request(
      {
        host,
        path: req.url,
        method: req.method,
        headers: { ...req.headers, host: `${host}` },
      },
      (proxyRes) => {
        res.writeHead(proxyRes.statusCode, proxyRes.headers);
        proxyRes.pipe(res);
      }
    );

    proxyReq.on("error", (err) => {
      console.warn(`[proxy] el backend no responde en ${host} (${err.code || err.message})`);
      if (!res.headersSent) res.writeHead(502, { "Content-Type": "application/json" });
      res.end(
        JSON.stringify({
          error: "BackendUnavailable",
          message: `No hay respuesta del backend en ${host}`,
        })
      );
    });

    req.pipe(proxyReq);
  };
}

module.exports = { createApiProxy };
