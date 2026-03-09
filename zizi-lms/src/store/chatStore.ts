import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface ChatSource {
  source: string;
  score: number;
}

export interface ChatMsg {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: ChatSource[];
  steps?: string[];
  streaming?: boolean;
  timestamp: number;
}

interface ChatStore {
  messages: ChatMsg[];
  isStreaming: boolean;
  conversationId: string;

  addMessage: (msg: ChatMsg) => void;
  appendToken: (id: string, token: string) => void;
  setMsgSources: (id: string, sources: ChatSource[]) => void;
  setMsgSteps: (id: string, steps: string[]) => void;
  pushStep: (id: string, step: string) => void;
  finishMessage: (id: string) => void;
  clearHistory: () => void;
}

export const useChatStore = create<ChatStore>()(
  persist(
    (set) => ({
      messages: [],
      isStreaming: false,
      conversationId: crypto.randomUUID?.() ?? Math.random().toString(36).slice(2),

      addMessage: (msg) =>
        set((s) => ({ messages: [...s.messages, msg] })),

      appendToken: (id, token) =>
        set((s) => ({
          messages: s.messages.map((m) =>
            m.id === id ? { ...m, content: m.content + token } : m
          ),
          isStreaming: true,
        })),

      setMsgSources: (id, sources) =>
        set((s) => ({
          messages: s.messages.map((m) => (m.id === id ? { ...m, sources } : m)),
        })),

      setMsgSteps: (id, steps) =>
        set((s) => ({
          messages: s.messages.map((m) => (m.id === id ? { ...m, steps } : m)),
        })),

      pushStep: (id, step) =>
        set((s) => ({
          messages: s.messages.map((m) =>
            m.id === id ? { ...m, steps: [...(m.steps || []), step] } : m
          ),
        })),

      finishMessage: (id) =>
        set((s) => ({
          isStreaming: false,
          messages: s.messages.map((m) =>
            m.id === id ? { ...m, streaming: false } : m
          ),
        })),

      clearHistory: () =>
        set({ messages: [], isStreaming: false }),
    }),
    {
      name: 'zizi-chat-store',
      partialize: (s) => ({ messages: s.messages.slice(-40) }), // keep last 40
    }
  )
);
