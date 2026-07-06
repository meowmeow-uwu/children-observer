import { create } from "zustand";
import type { ChildProfile } from "../types";

interface ChildState {
  children: ChildProfile[];
  selectedChildId: string | null;
  
  // Actions
  setChildren: (children: ChildProfile[]) => void;
  addChild: (child: ChildProfile) => void;
  selectChild: (childId: string | null) => void;
}

const mockChildren: ChildProfile[] = [
  {
    id: "child_01",
    name: "Bé Bo (Nguyễn Minh Hải)",
    age: 3,
    gender: "nam",
    avatarUrl: "https://lh3.googleusercontent.com/aida-public/AB6AXuAfMyD6gjCe8vpn60J432v-LPOTfDIAXhE0Jb7LOlk8m5b8EvsB-gaVxtZ2abyvG6eTHbxbJy63ooDwCbNoA1d9OlJdnk_dzAKIc8YzMqz3QWqLx6ytF3Js1zvVLoYFfoRaz6cihWdwR1x0OrZFxOkEIjjjKrUUC-ZACtkfXO9Pn8de-5ow52lwAF0JNF6FTh1s4nM15yyRuGOez-wGufnjQ6qaOpJ1gCEKGhF2zyHhGDr6hU4jhTWqYyBZn9ItzZF2EakxPdzyuA0k",
    notes: "Rất hay leo trèo và tò mò khu vực ban công."
  },
  {
    id: "child_02",
    name: "Bé Vy (Nguyễn Khánh Vy)",
    age: 5,
    gender: "nữ",
    avatarUrl: "https://lh3.googleusercontent.com/aida-public/AB6AXuBCI0FXHpLQfLFj-6UNQcNILtpX4Ajx_iVZ6ArMjZMDlobInLvawDiinSEI1I4aGrVGi411KmsEIXi_HFWgdRRFXimVDuO1VFNikXE0rAYlLvQVvqxFC8kxXeNJYUDyF7q_FCNC8ksbh__0ZzS1sjElTAOMfQcSfTOam24TsQebg6WDKnObDWlL-VSEU69WzQ7U9xhmZYDIWTOd6aYZXOoqVwKbBd2YlDUXwNDK0ypE2CEM5OBRbxCmp728suzlZ_obf1nTO9IDfxjP",
    notes: "Thích chạy nhảy quanh cầu thang."
  }
];

export const useChildStore = create<ChildState>((set) => ({
  children: mockChildren,
  selectedChildId: null,

  setChildren: (children) => set({ children }),
  addChild: (child) => set((state) => ({ children: [...state.children, child] })),
  selectChild: (selectedChildId) => set({ selectedChildId })
}));
