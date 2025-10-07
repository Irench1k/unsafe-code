const app = require("./src/app");

// Get configuration from environment variables with sensible defaults
const host = process.env.APP_HOST || "0.0.0.0";
const port = process.env.APP_PORT || 3000;

app.listen(port, host, () => {
  console.log(`Example app listening on http://${host}:${port}`);
});
