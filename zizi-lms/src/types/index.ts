export interface TopicSummary {
  id: string;
  name: string;
  description: string;
  concepts: string[];
  module_number: string;
  source_url: string;
  is_post: boolean;
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
