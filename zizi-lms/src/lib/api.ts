import type {
  TopicSummary,
  ByteContent,
  BuildContent,
  KGData,
  TopicNeighbors,
  SharePostResult,
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

export async function createSharePost(
  topicId: string,
  customMessage?: string
): Promise<SharePostResult> {
  return apiFetch<SharePostResult>('/api/share/create-post', {
    method: 'POST',
    body: JSON.stringify({ topic_id: topicId, custom_message: customMessage }),
  });
}
