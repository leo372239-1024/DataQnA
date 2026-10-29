/** 会话客户端状态（Zustand）：活跃问题 id、角色、暗色偏好。 */
import { create } from "zustand";
import { persist } from "zustand/middleware";

interface SessionState {
  activeQuestionId: string | null;
  roles: string[];
  dark: boolean;
  setActiveQuestion: (id: string | null) => void;
  setRoles: (roles: string[]) => void;
  setDark: (dark: boolean) => void;
}

export const useSessionStore = create<SessionState>()(
  persist(
    (set) => ({
      activeQuestionId: null,
      roles: ["analyst"],
      dark: false,
      setActiveQuestion: (id) => set({ activeQuestionId: id }),
      setRoles: (roles) => set({ roles }),
      setDark: (dark) => set({ dark }),
    }),
    { name: "dq-session" },
  ),
);
