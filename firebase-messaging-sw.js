// firebase-messaging-sw.js
importScripts('https://www.gstatic.com/firebasejs/11.0.2/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/11.0.2/firebase-messaging-compat.js');

// Firebase config (same as main app)
firebase.initializeApp({
    apiKey: "AIzaSyDui5MKg4sB4eEcMjgjVXnw-u6bLm90D4E",
    authDomain: "scribe-c7f13.firebaseapp.com",
    projectId: "scribe-c7f13",
    storageBucket: "scribe-c7f13.firebasestorage.app",
    messagingSenderId: "970064337409",
    appId: "1:970064337409:web:ab8ecc361e352c5025be00",
    measurementId: "G-NH06MQQ2J3"
});

// Retrieve messaging
const messaging = firebase.messaging();

// Background message handler
messaging.onBackgroundMessage(function (payload) {
    console.log('Received background message ', payload);

    // Show notification
    const notificationTitle = payload.notification?.title || 'New Message';
    const notificationOptions = {
        body: payload.notification?.body || 'You have a new message',
        icon: '/favicon.ico',
        badge: '/favicon.ico',
        data: payload.data
    };

    self.registration.showNotification(notificationTitle, notificationOptions);
});

// Handle notification click
self.addEventListener('notificationclick', function (event) {
    console.log('Notification click received.');
    event.notification.close();

    // Add custom logic here for notification click
    // For example, focus on the app window or navigate to a specific page
    event.waitUntil(
        clients.openWindow('http://localhost:8000/static/notification-test.html')
    );
});
