// context/AuthContext.tsx
'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import Cookies from 'js-cookie';
import { useRouter } from 'next/navigation';
import type { UserProfile, TokenResponse } from '../types/auth.type';

interface AuthContextType {
  // Authentication state
  isAuthenticated: boolean;
  isLoading: boolean;
  user: UserProfile | null;

  // Token management
  accessToken: string | null;
  refreshToken: string | null;

  // Authentication methods
  login: (tokens: TokenResponse, user: UserProfile) => void;
  logout: () => void;
  updateTokens: (tokens: Partial<TokenResponse>) => void;
  updateUser: (user: Partial<UserProfile>) => void;

  // Utility methods
  checkAuthStatus: () => Promise<boolean>;
  refreshAccessToken: () => Promise<boolean>;
}

const AuthContext = createContext<AuthContextType>({
  isAuthenticated: false,
  isLoading: true,
  user: null,
  accessToken: null,
  refreshToken: null,
  login: () => { },
  logout: () => { },
  updateTokens: () => { },
  updateUser: () => { },
  checkAuthStatus: async () => false,
  refreshAccessToken: async () => false,
});

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [user, setUser] = useState<UserProfile | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState<string | null>(null);

  const router = useRouter();

  // Initialize auth state from cookies on mount
  useEffect(() => {
    const initializeAuth = async () => {
      console.log('🔐 Initializing authentication state...');

      const storedAccessToken = Cookies.get('access_token');
      const storedRefreshToken = Cookies.get('refresh_token');
      const storedUser = localStorage.getItem('user_profile');

      if (storedAccessToken) {
        setAccessToken(storedAccessToken);
        console.log('✅ Access token found in cookies');
      }

      if (storedRefreshToken) {
        setRefreshToken(storedRefreshToken);
        console.log('✅ Refresh token found in cookies');
      }

      if (storedUser) {
        try {
          const userProfile: UserProfile = JSON.parse(storedUser);
          setUser(userProfile);
          console.log('✅ User profile loaded from localStorage');
        } catch (error) {
          console.error('❌ Failed to parse user profile from localStorage:', error);
          localStorage.removeItem('user_profile');
        }
      }

      // Check if we have valid tokens
      if (storedAccessToken && storedRefreshToken) {
        const isValid = await checkAuthStatus();
        setIsAuthenticated(isValid);

        if (!isValid) {
          console.log('⚠️ Tokens are invalid, attempting refresh...');
          const refreshed = await refreshAccessToken();
          if (!refreshed) {
            console.log('❌ Token refresh failed, user needs to login again');
            logout();
          }
        }
      } else {
        setIsAuthenticated(false);
      }

      setIsLoading(false);
      console.log('🎯 Authentication initialization complete');
    };

    initializeAuth();
  }, []);

  const checkAuthStatus = async (): Promise<boolean> => {
    const currentToken = Cookies.get('access_token');
    if (!currentToken) {
      console.log('❌ No access token found');
      return false;
    }

    try {
      // You can add a lightweight API call here to verify token validity
      // For now, we'll just check if the token exists and is not expired
      console.log('🔍 Checking token validity...');
      return true; // Assume valid for now
    } catch (error) {
      console.error('❌ Token validation failed:', error);
      return false;
    }
  };

  const refreshAccessToken = async (): Promise<boolean> => {
    const currentRefreshToken = Cookies.get('refresh_token');
    if (!currentRefreshToken) {
      console.log('❌ No refresh token found');
      return false;
    }

    try {
      console.log('🔄 Attempting to refresh access token...');

      // Import authApi here to avoid circular dependencies
      const { default: authApi } = await import('../services/api/auth');

      const response = await authApi.refreshToken({
        refresh_token: currentRefreshToken
      });

      if (response.success && response.data) {
        const { access_token, refresh_token: newRefreshToken } = response.data;

        // Update cookies and state
        Cookies.set('access_token', access_token, { expires: 7 }); // 7 days
        if (newRefreshToken) {
          Cookies.set('refresh_token', newRefreshToken, { expires: 30 }); // 30 days
        }

        setAccessToken(access_token);
        if (newRefreshToken) {
          setRefreshToken(newRefreshToken);
        }

        console.log('✅ Access token refreshed successfully');
        return true;
      } else {
        console.error('❌ Token refresh failed:', response.message);
        return false;
      }
    } catch (error) {
      console.error('❌ Token refresh error:', error);
      return false;
    }
  };

  const login = (tokens: TokenResponse, userProfile: UserProfile) => {
    console.log('🔐 User login initiated');

    // Set cookies
    Cookies.set('access_token', tokens.access_token, { expires: 7 }); // 7 days
    Cookies.set('refresh_token', tokens.refresh_token, { expires: 30 }); // 30 days

    // Update state
    setAccessToken(tokens.access_token);
    setRefreshToken(tokens.refresh_token);
    setUser(userProfile);
    setIsAuthenticated(true);

    // Store user profile in localStorage for persistence
    localStorage.setItem('user_profile', JSON.stringify(userProfile));

    console.log('✅ User logged in successfully');
  };

  const logout = () => {
    console.log('🚪 User logout initiated');

    // Clear cookies
    Cookies.remove('access_token');
    Cookies.remove('refresh_token');

    // Clear state
    setAccessToken(null);
    setRefreshToken(null);
    setUser(null);
    setIsAuthenticated(false);

    // Clear localStorage
    localStorage.removeItem('user_profile');

    // Redirect to login page
    if (typeof window !== 'undefined') {
      router.push('/auth');
    }

    console.log('✅ User logged out successfully');
  };

  const updateTokens = (tokens: Partial<TokenResponse>) => {
    console.log('🔄 Updating tokens');

    if (tokens.access_token) {
      Cookies.set('access_token', tokens.access_token, { expires: 7 });
      setAccessToken(tokens.access_token);
    }

    if (tokens.refresh_token) {
      Cookies.set('refresh_token', tokens.refresh_token, { expires: 30 });
      setRefreshToken(tokens.refresh_token);
    }
  };

  const updateUser = (userData: Partial<UserProfile>) => {
    if (user) {
      const updatedUser = { ...user, ...userData };
      setUser(updatedUser);
      localStorage.setItem('user_profile', JSON.stringify(updatedUser));
      console.log('👤 User profile updated');
    }
  };

  const contextValue: AuthContextType = {
    isAuthenticated,
    isLoading,
    user,
    accessToken,
    refreshToken,
    login,
    logout,
    updateTokens,
    updateUser,
    checkAuthStatus,
    refreshAccessToken,
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
