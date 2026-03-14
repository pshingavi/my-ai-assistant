export interface CachedByte {
  id?: number;
  topic_id: string;
  concept: string;
  topic_name: string;
  version: number;
  analogy: string;
  explanation: string;
  why_it_matters: string;
  emoji: string;
  image_prompt: string;
  image_url: string;
  image_local_path: string;
  sources: string[];
  created_at?: string;
  audio_url: string;
  audio_local_path: string;
}

export interface ByteContent {
  concept: string;
  topic_name: string;
  analogy: string;
  explanation: string;
  why_it_matters: string;
  emoji: string;
  sources: string[];
  image_prompt: string;
  image_url?: string;
  version?: number;
}

export interface BuildContent {
  concept: string;
  topic_name: string;
  code_snippet: string;
  language: string;
  explanation: string;
  run_notes: string;
  sources: string[];
}

export interface TopicSummary {
  id: string;
  name: string;
  description: string;
  concepts: string[];
  module_number: string;
  source_url: string;
  is_post: boolean;
}

export interface KGNode {
  id: string;
  name: string;
  is_post: boolean;
  module_number?: string;
}

export interface KGEdge {
  source: string;
  target: string;
  relation?: string;
}

export interface KGData {
  nodes: KGNode[];
  edges: KGEdge[];
}

export interface TopicNeighbors {
  prerequisites: TopicSummary[];
  next: TopicSummary[];
  related: TopicSummary[];
}

export interface SharePostResult {
  post_text: string;
  image_url?: string;
  topic_name: string;
}

export type LearningMode = 'learn' | 'build' | 'share';

// ── Claude Interaction (replaces P5Sketch) ────────────────────────────────────

export interface P5Step {
  step_index: number;
  title: string;
  description: string;
  code_snippet: string;
  language: string;
  explanation: string;
}

export interface P5Sketch {
  sketch_code: string;
  steps: P5Step[];
}
