'use client';

import { useRouter } from 'next/navigation';
import type { TopicSummary } from '@/src/types';
import { useLMSStore } from '@/src/store/lmsStore';

interface TopicSidebarProps {
  topics: TopicSummary[];
  currentTopicId: string;
}

function TopicItem({
  topic,
  isActive,
  isVisited,
  onClick,
}: {
  topic: TopicSummary;
  isActive: boolean;
  isVisited: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left px-3 py-2.5 rounded-lg transition-all duration-150 flex items-start gap-2"
      style={{
        background: isActive ? 'rgba(139,92,246,0.15)' : 'transparent',
        border: isActive ? '1px solid rgba(139,92,246,0.4)' : '1px solid transparent',
      }}
    >
      <span
        className="flex-shrink-0 mt-0.5 text-xs font-bold px-1.5 py-0.5 rounded"
        style={
          topic.is_post
            ? { background: 'rgba(34,211,238,0.15)', color: '#22d3ee', minWidth: 28, textAlign: 'center' as const }
            : { background: 'rgba(139,92,246,0.15)', color: '#8b5cf6', minWidth: 28, textAlign: 'center' as const }
        }
      >
        {topic.is_post ? '\u2736' : topic.module_number || '?'}
      </span>
      <span
        className="text-xs leading-snug font-medium"
        style={{
          color: isActive ? '#f1f5f9' : isVisited ? '#94a3b8' : '#64748b',
          display: '-webkit-box',
          WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical' as const,
          overflow: 'hidden',
        }}
      >
        {topic.name}
      </span>
      {isActive && (
        <span
          className="flex-shrink-0 ml-auto mt-1 w-1.5 h-1.5 rounded-full"
          style={{ background: '#8b5cf6' }}
        />
      )}
    </button>
  );
}

export default function TopicSidebar({ topics, currentTopicId }: TopicSidebarProps) {
  const router = useRouter();
  const { visitedTopicIds, setTopic } = useLMSStore();

  const courseTopics = topics.filter((t) => !t.is_post);
  const postTopics = topics.filter((t) => t.is_post);

  const handleTopicClick = (topicId: string) => {
    setTopic(topicId);
    router.push(`/learn/${topicId}`);
  };

  return (
    <div
      className="flex flex-col h-full overflow-hidden"
      style={{ background: '#0f0f16', borderRight: '1px solid rgba(139,92,246,0.1)' }}
    >
      {/* Header */}
      <div className="px-4 py-4" style={{ borderBottom: '1px solid rgba(139,92,246,0.1)' }}>
        <button onClick={() => router.push('/')} className="flex items-center gap-2 mb-2">
          <span className="text-xl" aria-label="lightning">&#9889;</span>
          <span className="font-extrabold text-sm" style={{ color: '#8b5cf6' }}>
            Zizi Byte
          </span>
        </button>
        <p className="text-xs" style={{ color: '#475569' }}>
          {topics.length} topics loaded
        </p>
      </div>

      {/* Topic list */}
      <div className="flex-1 overflow-y-auto py-3 px-2 space-y-4">
        {courseTopics.length > 0 && (
          <div>
            <p
              className="text-xs font-bold uppercase tracking-widest px-2 mb-2"
              style={{ color: '#475569' }}
            >
              Course Modules
            </p>
            <div className="space-y-0.5">
              {courseTopics.map((topic) => (
                <TopicItem
                  key={topic.id}
                  topic={topic}
                  isActive={topic.id === currentTopicId}
                  isVisited={visitedTopicIds.has(topic.id)}
                  onClick={() => handleTopicClick(topic.id)}
                />
              ))}
            </div>
          </div>
        )}

        {postTopics.length > 0 && (
          <div>
            <p
              className="text-xs font-bold uppercase tracking-widest px-2 mb-2"
              style={{ color: '#475569' }}
            >
              Generated Posts
            </p>
            <div className="space-y-0.5">
              {postTopics.map((topic) => (
                <TopicItem
                  key={topic.id}
                  topic={topic}
                  isActive={topic.id === currentTopicId}
                  isVisited={visitedTopicIds.has(topic.id)}
                  onClick={() => handleTopicClick(topic.id)}
                />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-3" style={{ borderTop: '1px solid rgba(139,92,246,0.1)' }}>
        <p className="text-xs text-center" style={{ color: '#334155' }}>
          Learn in bytes. Think in leaps.
        </p>
      </div>
    </div>
  );
}
