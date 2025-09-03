import React, { createContext, useContext, useState } from 'react';

type SidebarItem = 'home' | 'meeting' | 'setting' | 'store' | 'history';

interface SidebarContextType {
  selected: SidebarItem;
  setSelected: (item: SidebarItem) => void;
}

const SidebarContext = createContext<SidebarContextType | undefined>(undefined);

export const SidebarProvider = ({
  children,
}: {
  children: React.ReactNode;
}) => {
  const [selected, setSelectedState] = useState<SidebarItem>(() => {
    if (typeof window !== 'undefined') {
      const stored = window.localStorage.getItem('sidebar-selected');
      if (stored === 'home' || stored === 'meeting' || stored === 'setting' || stored === 'store' || stored === 'history')
        return stored;
    }
    return 'meeting';
  });

  const setSelected = (item: SidebarItem) => {
    setSelectedState(item);
    if (typeof window !== 'undefined') {
      window.localStorage.setItem('sidebar-selected', item);
    }
  };

  return (
    <SidebarContext.Provider value={{ selected, setSelected }}>
      {children}
    </SidebarContext.Provider>
  );
};

export const useSidebar = () => {
  const ctx = useContext(SidebarContext);
  if (!ctx) throw new Error('useSidebar must be used within SidebarProvider');
  return ctx;
};
