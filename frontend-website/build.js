const fs = require("node:fs");
const path = require("node:path");

const sourceDirectory = __dirname;
const outputDirectory = path.join(sourceDirectory, "dist");

function resolveApiBaseUrl() {
    const value = process.env.API_BASE_URL?.trim();
    // Si no está definido, o si apunta directamente a Render (que ahora se proxia via vercel.json),
    // dejamos apiBaseUrl vacío ("") para que el navegador use el mismo dominio de Vercel y evite problemas de CORS.
    if (!value || value.includes("onrender.com") || process.env.USE_API_PROXY === "true") {
        return "";
    }

    let url;
    try {
        url = new URL(value);
    } catch {
        throw new Error("API_BASE_URL must be a valid absolute HTTP or HTTPS URL.");
    }

    if (!["http:", "https:"].includes(url.protocol) || url.username || url.password || url.search || url.hash) {
        throw new Error("API_BASE_URL must use HTTP(S) and must not contain credentials, a query, or a fragment.");
    }

    return `${url.origin}${url.pathname.replace(/\/+$/, "")}`;
}

function optionalAnalyticsId(environmentVariable, pattern, label) {
    const value = process.env[environmentVariable]?.trim() || "";
    if (value && !pattern.test(value)) {
        throw new Error(`${environmentVariable} is not a valid ${label} identifier.`);
    }
    return value;
}

const config = {
    apiBaseUrl: resolveApiBaseUrl(),
    googleTagManagerId: optionalAnalyticsId("GTM_ID", /^GTM-[A-Z0-9]+$/, "Google Tag Manager"),
    googleAnalyticsId: optionalAnalyticsId("GA_MEASUREMENT_ID", /^G-[A-Z0-9]+$/, "Google Analytics 4"),
};

fs.mkdirSync(outputDirectory, { recursive: true });

for (const fileName of ["index.html", "product.html", "stores.html", "analytics.js", "vercel.json"]) {
    const sourcePath = path.join(sourceDirectory, fileName);
    if (!fs.existsSync(sourcePath)) continue;
    const outputPath = path.join(outputDirectory, fileName);
    let contents = fs.readFileSync(sourcePath, "utf8");

    if (fileName.endsWith(".html")) {
        const noscript = config.googleTagManagerId
            ? `<noscript><iframe src="https://www.googletagmanager.com/ns.html?id=${config.googleTagManagerId}" height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>`
            : "";
        contents = contents
            .replaceAll("<!-- ANALYTICS_NOSCRIPT -->", noscript)
            .replaceAll("__API_BASE_URL__", config.apiBaseUrl)
            .replaceAll("__GTM_ID__", config.googleTagManagerId)
            .replaceAll("__GA_MEASUREMENT_ID__", config.googleAnalyticsId);
        fs.writeFileSync(outputPath, contents);
    } else {
        fs.copyFileSync(sourcePath, outputPath);
    }
}

fs.writeFileSync(
    path.join(outputDirectory, "env-config.js"),
    `window.APP_CONFIG = Object.freeze(${JSON.stringify(config)});\n`
);
