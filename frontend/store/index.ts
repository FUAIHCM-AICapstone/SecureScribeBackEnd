// store/index.ts

import { configureStore } from '@reduxjs/toolkit';
import exampleReducer from './slices/exampleSlice';
import authReducer from './slices/authSlice';

const store = configureStore({
  reducer: {
    example: exampleReducer, // Add reducers here as you create more slices
    auth: authReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
export default store;
