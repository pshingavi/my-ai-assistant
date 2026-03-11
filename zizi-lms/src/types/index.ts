// Remotion animation props
export interface AnalogyRevealProps {
  concept: string;
  analogy: string;
  emoji: string;
  accentColor: string;
  keywords: string[];
}

export interface FlowNode {
  id: string;
  label: string;
  x: number;
  y: number;
  color: string;
}

export interface FlowEdge {
  fromId: string;
  toId: string;
  label?: string;
}

export interface ConceptFlowProps {
  concept: string;
  nodes: FlowNode[];
  edges: FlowEdge[];
  accentColor: string;
}

export type RemotionCompositionProps =
  | { type: 'analogy_reveal'; props: AnalogyRevealProps }
  | { type: 'concept_flow'; props: ConceptFlowProps }
  | { type: 'none' };

// Extended ByteContent with cache metadata
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
  animation_props: RemotionCompositionProps;
  sources: string[];
  created_at?: string;
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
  animation_props?: RemotionCompositionProps;
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
