import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { ByteContent, BuildContent, LearningMode } from '@/src/types';

interface LMSStore {
  currentTopicId: string | null;
  currentConceptIndex: number;
  currentMode: LearningMode;
  byteCache: Record<string, ByteContent>;
  buildCache: Record<string, BuildContent>;
  visitedTopicIds: Set<string>;

  setTopic: (id: string) => void;
  setConceptIndex: (i: number) => void;
  setMode: (mode: LearningMode) => void;
  cacheBytes: (key: string, content: ByteContent) => void;
  cacheBuild: (key: string, content: BuildContent) => void;
  markVisited: (id: string) => void;
  resetProgress: () => void;
}

export const useLMSStore = create<LMSStore>()(
  persist(
    (set) => ({
      currentTopicId: null,
      currentConceptIndex: 0,
      currentMode: 'learn',
      byteCache: {},
      buildCache: {},
      visitedTopicIds: new Set<string>(),

      setTopic: (id: string) =>
        set((state) => ({
          currentTopicId: id,
          currentConceptIndex: 0,
          visitedTopicIds: new Set(Array.from(state.visitedTopicIds).concat(id)),
        })),

      setConceptIndex: (i: number) => set({ currentConceptIndex: i }),

      setMode: (mode: LearningMode) => set({ currentMode: mode }),

      cacheBytes: (key: string, content: ByteContent) =>
        set((state) => ({
          byteCache: { ...state.byteCache, [key]: content },
        })),

      cacheBuild: (key: string, content: BuildContent) =>
        set((state) => ({
          buildCache: { ...state.buildCache, [key]: content },
        })),

      markVisited: (id: string) =>
        set((state) => ({
          visitedTopicIds: new Set(Array.from(state.visitedTopicIds).concat(id)),
        })),

      resetProgress: () =>
        set({ visitedTopicIds: new Set<string>() }),
    }),
    {
      name: 'zizi-lms-store',
      // Only persist lightweight navigation state — NOT content caches.
      // byteCache/buildCache are large and must stay fresh from the API.
      partialize: (state) => ({
        visitedTopicIds: Array.from(state.visitedTopicIds),
        currentMode: state.currentMode,
      }),
      merge: (persisted: unknown, current: LMSStore) => {
        const p = persisted as {
          visitedTopicIds?: string[];
          currentMode?: LearningMode;
        };
        return {
          ...current,
          visitedTopicIds: new Set(p?.visitedTopicIds || []),
          currentMode: p?.currentMode ?? 'learn',
          byteCache: {},
          buildCache: {},
        };
      },
    }
  )
);
