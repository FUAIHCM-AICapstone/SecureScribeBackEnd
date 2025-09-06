'use client';

import React, { useState } from 'react';
import Cookies from 'js-cookie';
import { showToast } from '@/hooks/useShowToast';
import { useTranslations } from 'next-intl';
import authApi from '@/services/api/auth';
import firebase from 'firebase/compat/app';
import 'firebase/compat/auth';

// Firebase configuration
const firebaseConfig = {
    apiKey: "AIzaSyDui5MKg4sB4eEcMjgjVXnw-u6bLm90D4E",
    authDomain: "scribe-c7f13.firebaseapp.com",
    projectId: "scribe-c7f13",
    storageBucket: "scribe-c7f13.firebasestorage.app",
    messagingSenderId: "970064337409",
    appId: "1:970064337409:web:ab8ecc361e352c5025be00",
    measurementId: "G-NH06MQQ2J3"
};

interface FirebaseAuthProps {
    onSuccess?: () => void;
}

const FirebaseAuth: React.FC<FirebaseAuthProps> = ({ onSuccess }) => {
    const [loading, setLoading] = useState(false);
    const t = useTranslations('AuthForm');

    const handleGoogleLogin = async () => {
        setLoading(true);
        try {
            if (!firebase.apps.length) {
                firebase.initializeApp(firebaseConfig);
            }
            const auth = firebase.auth();
            const provider = new firebase.auth.GoogleAuthProvider();

            const result = await auth.signInWithPopup(provider);
            const user = result.user;
            if (!user) {
                throw new Error(t('userNotFound'));
            }
            const idToken = await user.getIdToken();

            const response = await authApi.firebaseLogin({ id_token: idToken });

            if (response.success && response.data) {
                Cookies.set('access_token', response.data.token.access_token, { expires: 7 });
                Cookies.set('refresh_token', response.data.token.refresh_token, { expires: 30 });
                onSuccess?.();
            } else {
                throw new Error(response?.message || t('networkError'));
            }
        } catch (error: any) {
            console.error('Firebase login error:', error);
            let errorMessage = t('networkError');

            // Handle specific Firebase errors
            if (error.code === 'auth/invalid-credential') {
                errorMessage = t('invalidCredentials');
            } else if (error.code === 'auth/user-disabled') {
                errorMessage = t('userDisabled');
            } else if (error.code === 'auth/user-not-found') {
                errorMessage = t('userNotFound');
            } else if (error.code === 'auth/popup-closed-by-user') {
                errorMessage = t('loginCancelled');
            } else if (error.code === 'auth/popup-blocked') {
                errorMessage = t('popupBlocked');
            } else if (error.code === 'auth/network-request-failed') {
                errorMessage = t('networkErrorConnection');
            } else if (error.message) {
                // Check for token timing and validity errors
                if (error.message.includes('Token used too early') ||
                    error.message.includes('clock is set correctly') ||
                    error.message.includes('Invalid Google token')) {
                    errorMessage = t('tokenUsedTooEarly');
                } else if (error.message.includes('Invalid token') ||
                    error.message.includes('Token expired')) {
                    errorMessage = t('invalidToken');
                } else {
                    errorMessage = error.message;
                }
            }

            showToast('error', errorMessage, 4000);
        } finally {
            setLoading(false);
        }
    };

    return (
        <button
            onClick={handleGoogleLogin}
            disabled={loading}
            className="w-full flex items-center justify-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
        >
            <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
            </svg>
            {loading ? t('loginButton') : 'Đăng nhập với Google'}
        </button>
    );
};

export default FirebaseAuth;
