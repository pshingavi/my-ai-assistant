'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import toast from 'react-hot-toast';
import { createSharePost } from '@/src/lib/api';
import type { TopicSummary } from '@/src/types';

interface ShareModalProps {
  topic: TopicSummary;
}

export default function ShareModal({ topic }: ShareModalProps) {
  const [loading, setLoading] = useState(false);
  const [postText, setPostText] = useState('');
  const [imageUrl, setImageUrl] = useState('');
  const [isDuplicate, setIsDuplicate] = useState(false);
  const [duplicateReason, setDuplicateReason] = useState('');
  const [customMessage, setCustomMessage] = useState('');
  const [copied, setCopied] = useState(false);

  const handleGenerate = async () => {
    setLoading(true);
    setPostText('');
    setImageUrl('');
    setIsDuplicate(false);
    setCopied(false);
    try {
      const result = await createSharePost(topic.id, customMessage || undefined);
      // Handle both structured and raw responses
      const r = result as unknown as Record<string, unknown>;
      if (r.is_duplicate) {
        setIsDuplicate(true);
        setDuplicateReason((r.reason as string) || 'This topic was already posted recently.');
      } else {
        const text =
          (r.post_text as string) ||
          (r.post as string) ||
          (r.content as string) ||
          '';
        setPostText(text);
        setImageUrl((r.image_url as string) || '');
        if (text) toast.success('LinkedIn post generated!');
      }
    } catch {
      toast.error('Failed to generate post — is the API server running?');
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(postText);
      setCopied(true);
      toast.success('Copied to clipboard!');
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error('Failed to copy');
    }
  };

  return (
    <div className="space-y-5 max-w-2xl">
      {/* Topic summary card */}
      <div
        className="rounded-2xl p-5"
        style={{ background: 'rgba(139,92,246,0.06)', border: '1px solid rgba(139,92,246,0.2)' }}
      >
        <div className="flex items-start justify-between gap-3 mb-2">
          <h3 className="text-base font-bold" style={{ color: '#f1f5f9' }}>
            {topic.name}
          </h3>
          {topic.module_number && (
            <span className="badge-module shrink-0">Module {topic.module_number}</span>
          )}
        </div>
        <p className="text-sm mb-4" style={{ color: '#64748b' }}>
          {topic.description}
        </p>
        <div className="flex flex-wrap gap-1.5">
          {topic.concepts.map((c) => (
            <span
              key={c}
              className="px-2 py-0.5 rounded-full text-xs"
              style={{ background: 'rgba(139,92,246,0.12)', color: '#a78bfa', border: '1px solid rgba(139,92,246,0.2)' }}
            >
              {c}
            </span>
          ))}
        </div>
      </div>

      {/* Custom angle */}
      <div>
        <label className="block text-xs font-semibold mb-1.5" style={{ color: '#64748b' }}>
          Custom angle (optional)
        </label>
        <input
          value={customMessage}
          onChange={(e) => setCustomMessage(e.target.value)}
          placeholder={`e.g. "Focus on ${topic.name} for junior ML engineers"`}
          className="w-full rounded-xl px-4 py-2.5 text-sm outline-none transition-colors"
          style={{
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(139,92,246,0.2)',
            color: '#f1f5f9',
          }}
          onFocus={(e) => (e.target.style.borderColor = 'rgba(139,92,246,0.5)')}
          onBlur={(e) => (e.target.style.borderColor = 'rgba(139,92,246,0.2)')}
        />
      </div>

      {/* Generate button */}
      <button
        onClick={handleGenerate}
        disabled={loading}
        className="w-full py-3 rounded-xl font-semibold text-white transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        style={{
          background: loading
            ? 'rgba(139,92,246,0.4)'
            : 'linear-gradient(135deg, #8b5cf6 0%, #22d3ee 100%)',
          boxShadow: loading ? 'none' : '0 0 20px rgba(139,92,246,0.3)',
        }}
      >
        {loading ? (
          <>
            <span
              className="w-4 h-4 rounded-full border-2 border-t-transparent animate-spin"
              style={{ borderColor: 'white', borderTopColor: 'transparent' }}
            />
            Generating LinkedIn Post...
          </>
        ) : (
          <>{'\uD83D\uDE80'} Generate LinkedIn Post</>
        )}
      </button>

      <AnimatePresence>
        {/* Duplicate warning */}
        {isDuplicate && (
          <motion.div
            key="duplicate"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="rounded-xl p-4 text-sm"
            style={{
              background: 'rgba(250,204,21,0.08)',
              border: '1px solid rgba(250,204,21,0.25)',
              color: '#fde68a',
            }}
          >
            <span className="font-semibold">Duplicate detected:</span> {duplicateReason}
          </motion.div>
        )}

        {/* Post result */}
        {postText && (
          <motion.div
            key="post-result"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="space-y-4"
          >
            <div className="relative">
              <div
                className="text-xs font-semibold mb-2 flex items-center justify-between"
                style={{ color: '#475569' }}
              >
                <span>LinkedIn Post</span>
                <button
                  onClick={handleCopy}
                  className="flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium transition-all duration-200"
                  style={{
                    background: copied ? 'rgba(34,211,238,0.15)' : 'rgba(139,92,246,0.15)',
                    color: copied ? '#22d3ee' : '#8b5cf6',
                    border: copied ? '1px solid rgba(34,211,238,0.3)' : '1px solid rgba(139,92,246,0.3)',
                  }}
                >
                  {copied ? (
                    <>{'\u2713'} Copied!</>
                  ) : (
                    <>{'\uD83D\uDCCB'} Copy Post</>
                  )}
                </button>
              </div>
              <textarea
                readOnly
                value={postText}
                rows={12}
                className="w-full rounded-xl px-4 py-3 text-sm resize-none outline-none"
                style={{
                  background: 'rgba(255,255,255,0.03)',
                  border: '1px solid rgba(255,255,255,0.08)',
                  color: '#e2e8f0',
                  fontFamily: 'Inter, sans-serif',
                  lineHeight: 1.6,
                }}
              />
            </div>

            {/* Generated image */}
            {imageUrl && (
              <div>
                <p className="text-xs font-semibold mb-2" style={{ color: '#475569' }}>
                  Generated Poster
                </p>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={imageUrl}
                  alt="Generated poster for LinkedIn post"
                  className="w-full rounded-xl"
                  style={{ border: '1px solid rgba(139,92,246,0.2)' }}
                />
                <a
                  href={imageUrl}
                  download
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-2 block text-center text-xs transition-colors"
                  style={{ color: '#8b5cf6' }}
                >
                  Download image &rarr;
                </a>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
