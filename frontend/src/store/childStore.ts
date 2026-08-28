import { create } from "zustand";
import type { ChildProfile } from "../types";

interface ChildState {
  children: ChildProfile[];
  selectedChildId: string | null;

  // Actions
  loadForUser: (userId: string) => void;
  addChild: (child: ChildProfile) => void;
  removeChild: (childId: string) => void;
  selectChild: (childId: string | null) => void;
  reset: () => void;
}

const STORAGE_PREFIX = "safekid_children_";

/** Lấy key localStorage riêng theo userId */
const storageKey = (userId: string) => `${STORAGE_PREFIX}${userId}`;

const readFromStorage = (userId: string): ChildProfile[] => {
  try {
    const raw = localStorage.getItem(storageKey(userId));
    return raw ? (JSON.parse(raw) as ChildProfile[]) : [];
  } catch {
    return [];
  }
};

const writeToStorage = (userId: string, children: ChildProfile[]) => {
  localStorage.setItem(storageKey(userId), JSON.stringify(children));
};

let currentUserId: string | null = null;

export const useChildStore = create<ChildState>((set) => ({
  children: [],
  selectedChildId: null,

  loadForUser: (userId: string) => {
    currentUserId = userId;
    const saved = readFromStorage(userId);
    set({ children: saved, selectedChildId: null });
  },

  addChild: (child) => {
    set((state) => {
      const updated = [...state.children, child];
      if (currentUserId) writeToStorage(currentUserId, updated);
      return { children: updated };
    });
  },

  removeChild: (childId) => {
    set((state) => {
      const updated = state.children.filter((c) => c.id !== childId);
      if (currentUserId) writeToStorage(currentUserId, updated);
      return { children: updated };
    });
  },

  selectChild: (selectedChildId) => set({ selectedChildId }),

  reset: () => {
    currentUserId = null;
    set({ children: [], selectedChildId: null });
  },
}));
