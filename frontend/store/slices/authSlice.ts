'use client';

import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import Cookies from 'js-cookie';
import authApi from '@/services/api/auth';
import type { MeResponse } from '../../types/auth.type';
import type { AuthState } from '../../types/common.type';

// Initial state matching AuthState interface
const initialState: AuthState = {
    isAuthenticated: false,
    isLoading: false,
    user: null,
    error: null,
};

// Async thunk to fetch current user info
export const fetchMe = createAsyncThunk<
    MeResponse,
    void,
    { rejectValue: string }
>('auth/fetchMe', async (_, { rejectWithValue }) => {
    try {
        const accessToken = Cookies.get('access_token');
        if (!accessToken) {
            return rejectWithValue('No access token found');
        }
        authApi.setToken?.(accessToken); // Only if setToken exists
        const res = await authApi.getMe();
        if (res && res.success && res.data) {
            return res.data;
        } else {
            return rejectWithValue(res?.message || 'Failed to fetch user info');
        }
    } catch (err: any) {
        return rejectWithValue(
            err?.response?.data?.message || err?.message || 'Failed to fetch user info'
        );
    }
});

const authSlice = createSlice({
    name: 'auth',
    initialState,
    reducers: {
        login(state, action: PayloadAction<MeResponse | null>) {
            state.isAuthenticated = true;
            state.user = action.payload;
            state.error = null;
            state.isLoading = false;
        },
        logout(state) {
            state.isAuthenticated = false;
            state.user = null;
            state.error = null;
            state.isLoading = false;
        },
        setUser(state, action: PayloadAction<MeResponse | null>) {
            state.user = action.payload;
        },
        clearError(state) {
            state.error = null;
        },
    },
    extraReducers: (builder) => {
        builder
            .addCase(fetchMe.pending, (state) => {
                state.isLoading = true;
                state.error = null;
            })
            .addCase(fetchMe.fulfilled, (state, action) => {
                state.isLoading = false;
                state.user = action.payload;
                state.isAuthenticated = true;
                state.error = null;
            })
            .addCase(fetchMe.rejected, (state, action) => {
                state.isLoading = false;
                state.error = action.payload || 'Failed to fetch user info';
                state.isAuthenticated = false;
                state.user = null;
            });
    },
});

export const { login, logout, setUser, clearError } = authSlice.actions;
export default authSlice.reducer;
