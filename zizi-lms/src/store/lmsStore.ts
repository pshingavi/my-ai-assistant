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
    }),
    {
      name: 'zizi-lms-store',
      partialize: (state) => ({
        visitedTopicIds: Array.from(state.visitedTopicIds),
        byteCache: state.byteCache,
        buildCache: state.buildCache,
      }),
      merge: (persisted: unknown, current: LMSStore) => {
        const p = persisted as {
          visitedTopicIds?: string[];
          byteCache?: Record<string, ByteContent>;
          buildCache?: Record<string, BuildContent>;
        };
        return {
          ...current,
          visitedTopicIds: new Set(p?.visitedTopicIds || []),
          byteCache: p?.byteCache || {},
          buildCache: p?.buildCache || {},
        };
      },
    }
  )
);
