import type {
  TopicSummary,
  ByteContent,
  BuildContent,
  KGData,
  TopicNeighbors,
  SharePostResult,
  CachedByte,
  P5Sketch,
} from '@/src/types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_URL}${path}`;
  const res = await fetch(url, {
    cache: 'no-store',
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options?.headers || {}),
    },
  });

  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API error ${res.status}: ${text}`);
  }

  return res.json() as Promise<T>;
}

export async function fetchTopics(): Promise<TopicSummary[]> {
  const data = await apiFetch<{ topics: TopicSummary[] }>('/api/topics');
  return data.topics;
}

export async function fetchTopic(id: string): Promise<TopicSummary> {
  return apiFetch<TopicSummary>(`/api/topics/${id}`);
}

export async function fetchTopicNeighbors(id: string): Promise<TopicNeighbors> {
  return apiFetch<TopicNeighbors>(`/api/topics/${id}/neighbors`);
}

export async function fetchKG(): Promise<KGData> {
  return apiFetch<KGData>('/api/kg');
}

export async function generateBytes(
  topicId: string,
  concept: string
): Promise<ByteContent> {
  return apiFetch<ByteContent>('/api/bytes/generate', {
    method: 'POST',
    body: JSON.stringify({ topic_id: topicId, concept }),
  });
}

export async function generateBuild(
  topicId: string,
  concept: string
): Promise<BuildContent> {
  return apiFetch<BuildContent>('/api/build/generate', {
    method: 'POST',
    body: JSON.stringify({ topic_id: topicId, concept }),
  });
}

export async function fetchCachedByte(topicId: string, concept: string): Promise<CachedByte | null> {
  try {
    return await apiFetch<CachedByte>(`/api/bytes/cached/${encodeURIComponent(topicId)}/${encodeURIComponent(concept)}`);
  } catch {
    return null;
  }
}

export async function regenerateByte(topicId: string, concept: string): Promise<CachedByte> {
  return apiFetch<CachedByte>('/api/bytes/regenerate', {
    method: 'POST',
    body: JSON.stringify({ topic_id: topicId, concept }),
  });
}

export async function triggerWarmCache(topicIds?: string[]): Promise<{ topics_queued: number }> {
  return apiFetch('/api/bytes/warm', {
    method: 'POST',
    body: JSON.stringify({ topic_ids: topicIds }),
  });
}

export async function createSharePost(
  topicId: string,
  concept: string,
  analogy?: string,
  imageUrl?: string,
  customMessage?: string
): Promise<SharePostResult> {
  return apiFetch<SharePostResult>('/api/share/create-post', {
    method: 'POST',
    body: JSON.stringify({ topic_id: topicId, concept, analogy, image_url: imageUrl, custom_message: customMessage }),
  });
}

// ── P5 Sketch API ──────────────────────────────────────────────────────────────

export async function fetchP5Sketch(topicId: string, concept: string): Promise<P5Sketch> {
  return apiFetch<P5Sketch>(
    `/api/topic/${encodeURIComponent(topicId)}/concept/${encodeURIComponent(concept)}/p5sketch`
  );
}

export async function regenerateWithAnalogy(
  topicId: string,
  concept: string,
  analogy?: string
): Promise<{ byte: CachedByte; sketch_code: string; steps: P5Sketch['steps'] }> {
  return apiFetch(
    `/api/topic/${encodeURIComponent(topicId)}/concept/${encodeURIComponent(concept)}/p5sketch/regenerate`,
    {
      method: 'POST',
      body: JSON.stringify({ analogy: analogy || null }),
    }
  );
}

export async function fetchAnalogySuggestions(
  topicId: string,
  concept: string
): Promise<string[]> {
  const data = await apiFetch<{ suggestions: string[] }>(
    `/api/topic/${encodeURIComponent(topicId)}/concept/${encodeURIComponent(concept)}/analogy-suggestions`
  );
  return data.suggestions;
}

export async function fetchClaudeInteraction(topicId: string, concept: string): Promise<P5Sketch> {
  return apiFetch<P5Sketch>(
    `/api/topic/${encodeURIComponent(topicId)}/concept/${encodeURIComponent(concept)}/claude-interaction`
  );
}

export function downloadNotebook(topicId: string, concept: string): void {
  const url = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'}/api/topic/${encodeURIComponent(topicId)}/concept/${encodeURIComponent(concept)}/notebook`;
  const a = document.createElement('a');
  a.href = url;
  a.download = `${concept.toLowerCase().replace(/\s+/g, '_')}.ipynb`;
  a.click();
}
