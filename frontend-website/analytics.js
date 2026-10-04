(function configureAnalytics() {
    const config = window.APP_CONFIG || {};
    const googleTagManagerId = config.googleTagManagerId || "";
    const googleAnalyticsId = config.googleAnalyticsId || "";

    if (googleTagManagerId) {
        window.dataLayer = window.dataLayer || [];
        window.dataLayer.push({
            "gtm.start": new Date().getTime(),
            event: "gtm.js"
        });

        const firstScript = document.getElementsByTagName("script")[0];
        const tagManagerScript = document.createElement("script");
        tagManagerScript.async = true;
        tagManagerScript.src =
            `https://www.googletagmanager.com/gtm.js?id=${encodeURIComponent(googleTagManagerId)}`;
        firstScript.parentNode.insertBefore(tagManagerScript, firstScript);
    }

    if (googleAnalyticsId) {
        window.dataLayer = window.dataLayer || [];
        window.gtag = function gtag() {
            window.dataLayer.push(arguments);
        };

        const analyticsScript = document.createElement("script");
        analyticsScript.async = true;
        analyticsScript.src =
            `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(googleAnalyticsId)}`;
        document.head.appendChild(analyticsScript);

        window.gtag("js", new Date());
        window.gtag("config", googleAnalyticsId, { send_page_view: true });
    }
})();
