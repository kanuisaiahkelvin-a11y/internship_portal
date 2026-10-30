/* Registers the service worker and drives the "Install app" affordances. */
(function () {
    'use strict';

    // --- Service worker -----------------------------------------------------
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', function () {
            navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(function () {
                // Offline support is an enhancement; ignore failures.
            });
        });
    }

    // --- Android / desktop install prompt -----------------------------------
    var installItem = document.getElementById('pwa-install-item');
    var installButton = document.getElementById('pwa-install');
    var deferredPrompt = null;

    window.addEventListener('beforeinstallprompt', function (event) {
        event.preventDefault();
        deferredPrompt = event;
        if (installItem) {
            installItem.classList.remove('d-none');
        }
    });

    if (installButton) {
        installButton.addEventListener('click', function () {
            if (!deferredPrompt) {
                return;
            }
            deferredPrompt.prompt();
            deferredPrompt.userChoice.then(function () {
                deferredPrompt = null;
                if (installItem) {
                    installItem.classList.add('d-none');
                }
            });
        });
    }

    window.addEventListener('appinstalled', function () {
        deferredPrompt = null;
        if (installItem) {
            installItem.classList.add('d-none');
        }
    });

    // --- iOS hint (Safari has no beforeinstallprompt) -----------------------
    var hint = document.getElementById('pwa-ios-hint');
    var hintClose = document.getElementById('pwa-hint-close');
    var isIos = /iphone|ipad|ipod/i.test(window.navigator.userAgent);
    var isStandalone =
        window.matchMedia('(display-mode: standalone)').matches ||
        window.navigator.standalone === true;

    if (hint && isIos && !isStandalone) {
        var dismissed = false;
        try {
            dismissed = window.localStorage.getItem('internlink-pwa-hint') === '1';
        } catch (error) {
            dismissed = false;
        }
        if (!dismissed) {
            hint.classList.remove('d-none');
        }
        if (hintClose) {
            hintClose.addEventListener('click', function () {
                hint.classList.add('d-none');
                try {
                    window.localStorage.setItem('internlink-pwa-hint', '1');
                } catch (error) {
                    // Private browsing; the hint simply reappears next visit.
                }
            });
        }
    }
})();
