// components/layout/Sidebar.tsx
'use client';

import React, { useState } from 'react';
import { useSidebar } from '@/context/SidebarContext';
import { useAuth } from '@/context/AuthContext';
import { useDispatch } from 'react-redux';
import { logout as logoutRedux } from '@/store/slices/authSlice';
import { FaUserCircle, FaSignOutAlt } from 'react-icons/fa';
import { FiHome, FiUsers, FiSettings, FiShoppingCart, FiClock } from 'react-icons/fi';
import { useTranslations } from 'next-intl';
import { usePathname } from 'next/navigation';
import Image from 'next/image';
import { useQuery } from '@tanstack/react-query';
import { IoFish } from "react-icons/io5";
import authApi from '@/services/api/auth';
import { showToast } from '@/hooks/useShowToast';

export default function Sidebar() {
  const t = useTranslations('Sidebar');
  const [collapsed, setCollapsed] = useState(true);
  const sidebarWidth = collapsed ? 64 : 240;
  const { logout: logoutContext } = useAuth();
  const dispatch = useDispatch();
  const { selected, setSelected } = useSidebar();
  const pathname = usePathname();

  // Check if we're on the group route
  const isGroupRoute = pathname.includes('/group');

  // Fetch user info using React Query
  const { data, isLoading } = useQuery({
    queryKey: ['me'],
    queryFn: () => authApi.getMe().then((res) => res.data),
    // Refetch every 5 seconds to keep fish balance realtime
    refetchInterval: 50000,
    refetchIntervalInBackground: true,
  });
  const user = data as any;
  const profilePicture = user?.profile_picture;
  const displayName =
    user?.name || user?.username || user?.email || t('userAvatar');

  // Logout handler
  const handleLogout = async () => {
    try {
      await authApi.logout();
      // Remove tokens from cookies
      document.cookie = 'access_token=; Max-Age=0; path=/;';
      document.cookie = 'refresh_token=; Max-Age=0; path=/;';
      // Update context and redux
      logoutContext();
      dispatch(logoutRedux());

      window.location.reload();
    } catch (e) {
      showToast('error', `${e}`);
      // Optionally: show error toast
    }
  };

  return (
    <aside
      className="h-full flex-shrink-0 bg-[var(--surface-color)] text-[var(--text-color)] shadow-md p-0 transition-all duration-200"
      style={{
        width: sidebarWidth,
        minWidth: collapsed ? 64 : 180,
        maxWidth: collapsed ? 64 : 360,
        resize: 'horizontal',
        overflow: 'hidden',
      }}
      aria-label={t('sidebarAriaLabel')}
    >
      <div className="h-full flex flex-col">
        {/* Collapse/Expand Button */}
        <button
          className="top-0 right-0 z-10 bg-[var(--surface-color)] p-1 hover:bg-[var(--card-bg)] transition-colors"
          style={{ outline: 'none' }}
          aria-label={collapsed ? t('expandSidebar') : t('collapseSidebar')}
          onClick={() => setCollapsed((c) => !c)}
        >
          <span className="sr-only">
            {collapsed ? t('expandSidebar') : t('collapseSidebar')}
          </span>
          <svg width="20" height="20" fill="currentColor"
            viewBox="0 0 20 20">
            {collapsed ? (
              <path d="M7 5l5 5-5 5V5z" />
            ) : (
              <path d="M13 5l-5 5 5 5V5z" />
            )}
          </svg>
        </button>
        {/* Profile */}
        <div
          className={`flex flex-col items-center justify-center pt-2 pb-4 transition-all duration-200 ${collapsed ? 'px-0' : ''}`}
        >
          {isLoading ? (
            <div className="w-20 h-20 rounded-full bg-[var(--card-bg)] animate-pulse mb-2" />
          ) : profilePicture ? (
            <Image
              src={profilePicture}
              alt="Profile"
              width={collapsed ? 40 : 80}
              height={collapsed ? 40 : 80}
              className="rounded-full object-cover border-2 border-[var(--primary-color)] shadow mb-2"
            />
          ) : (
            <FaUserCircle
              size={collapsed ? 32 : 64}
              className="text-[var(--primary-color)] mb-2"
            />
          )}
          {!collapsed && (
            <span className="font-semibold text-base text-center break-words max-w-[160px]">
              {isLoading ? '...' : displayName}
            </span>
          )}
          {!collapsed && !isLoading && (
            <div className="text-sm text-center mt-1 flex flex-row justify-center items-center gap-1">
              <span className="font-medium"><IoFish size={16} /></span>
              <span className="text-[var(--primary-color)]">{user?.fish_balance ?? 0}</span>
            </div>
          )}
        </div>
        {/* Navigation */}
        <nav
          className={`flex flex-col gap-6 p-4 text-lg ${collapsed ? 'items-center justify-center' : 'items-start justify-start'}`}
        >
          <button
            className={`flex items-center gap-3 w-full ${collapsed ? 'justify-center' : 'justify-start'} ${selected === 'home' ? 'text-[var(--primary-color)] font-semibold' : ''}`}
            onClick={() => setSelected('home')}
          >
            <FiHome size={20} />
            {!collapsed && <span>{t('home')}</span>}
          </button>
          <button
            className={`flex items-center gap-3 w-full ${collapsed ? 'justify-center' : 'justify-start'} ${selected === 'meeting' ? 'text-[var(--primary-color)] font-semibold' : ''}`}
            onClick={() => setSelected('meeting')}
          >
            <FiUsers size={20} />
            {!collapsed && <span>{isGroupRoute ? 'Groups' : t('meeting')}</span>}
          </button>
          <button
            className={`flex items-center gap-3 w-full ${collapsed ? 'justify-center' : 'justify-start'} ${selected === 'setting' ? 'text-[var(--primary-color)] font-semibold' : ''}`}
            onClick={() => setSelected('setting')}
          >
            <FiSettings size={20} />
            {!collapsed && <span>{t('setting')}</span>}
          </button>
          <button
            className={`flex items-center gap-3 w-full ${collapsed ? 'justify-center' : 'justify-start'} ${selected === 'store' ? 'text-[var(--primary-color)] font-semibold' : ''}`}
            onClick={() => setSelected('store')}
          >
            <FiShoppingCart size={20} />
            {!collapsed && <span>{t('store')}</span>}
          </button>
          <button
            className={`flex items-center gap-3 w-full ${collapsed ? 'justify-center' : 'justify-start'} ${selected === 'history' ? 'text-[var(--primary-color)] font-semibold' : ''}`}
            onClick={() => setSelected('history')}
          >
            <FiClock size={20} />
            {!collapsed && <span>History</span>}
          </button>
        </nav>

        {/* Logout */}
        <div
          className={`mt-auto p-4 border-t border-[var(--border-color)] ${collapsed ? 'flex justify-center' : ''}`}
        >
          <button
            className={`flex items-center gap-3 ${collapsed ? '' : 'w-full'} text-[var(--error-color)] hover:text-red-600 transition-colors`}
            onClick={handleLogout}
          >
            <FaSignOutAlt size={20} />
            {!collapsed && <span>{t('logout')}</span>}
          </button>
        </div>
      </div>
    </aside>
  );
}
