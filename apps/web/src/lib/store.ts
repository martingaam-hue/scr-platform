import { create } from "zustand";

interface SidebarState {
  isOpen: boolean;
  toggle: () => void;
  open: () => void;
  close: () => void;
}

export const useSidebarStore = create<SidebarState>((set) => ({
  isOpen: true,
  toggle: () => set((state) => ({ isOpen: !state.isOpen })),
  open: () => set({ isOpen: true }),
  close: () => set({ isOpen: false }),
}));

interface GlobalFilterState {
  search: string;
  setSearch: (search: string) => void;
}

export const useGlobalFilterStore = create<GlobalFilterState>((set) => ({
  search: "",
  setSearch: (search) => set({ search }),
}));
