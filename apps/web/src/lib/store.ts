import { create } from "zustand";

// ── Ralph AI store ─────────────────────────────────────────────────────────

interface RalphState {
  isOpen: boolean;
  toggle: () => void;
  open: () => void;
  close: () => void;
  activeConversationId: string | null;
  setActiveConversationId: (id: string | null) => void;
}

export const useRalphStore = create<RalphState>((set) => ({
  isOpen: false,
  toggle: () => set((s) => ({ isOpen: !s.isOpen })),
  open: () => set({ isOpen: true }),
  close: () => set({ isOpen: false }),
  activeConversationId: null,
  setActiveConversationId: (id) => set({ activeConversationId: id }),
}));

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

interface NotificationState {
  unreadCount: number;
  setUnreadCount: (count: number) => void;
  increment: () => void;
  decrement: () => void;
}

export const useNotificationStore = create<NotificationState>((set) => ({
  unreadCount: 0,
  setUnreadCount: (count) => set({ unreadCount: count }),
  increment: () => set((state) => ({ unreadCount: state.unreadCount + 1 })),
  decrement: () =>
    set((state) => ({ unreadCount: Math.max(0, state.unreadCount - 1) })),
}));
