'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import toast from 'react-hot-toast';
import { createSharePost, downloadNotebook } from '@/src/lib/api';
import type { TopicSummary } from '@/src/types';

interface ShareModalProps {
  topic: TopicSummary;
  currentConcept: string;
  byteAnalogy?: string;
  byteImageUrl?: string;
}

export default function ShareModal({ topic, currentConcept, byteAnalogy, byteImageUrl }: ShareModalProps) {
  const [loading, setLoading] = useState(false);
  const [postText, setPostText] = useState('');
  const [editablePost, setEditablePost] = useState('');
  const [isDuplicate, setIsDuplicate] = useState(false);
  const [duplicateReason, setDuplicateReason] = useState('');
  const [customMessage, setCustomMessage] = useState('');
  const [copied, setCopied] = useState(false);

  // Images are served by Next.js static at /generated/images/... — use relative path directly
  const resolvedImageUrl = byteImageUrl?.startsWith('http')
    ? byteImageUrl
    : byteImageUrl || '';

  const handleGenerate = async () => {
    setLoading(true);
    setPostText('');
    setIsDuplicate(false);
    setCopied(false);
    try {
      const result = await createSharePost(topic.id, currentConcept, byteAnalogy, byteImageUrl, customMessage || undefined);
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
        setEditablePost(text);
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
      await navigator.clipboard.writeText(editablePost || postText);
      setCopied(true);
      toast.success('Copied to clipboard!');
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error('Failed to copy');
    }
  };

  const handlePostToLinkedIn = () => {
    const text = editablePost || postText;
    if (!text) return;
    const url = `https://www.linkedin.com/feed/?shareActive=true&text=${encodeURIComponent(text)}`;
    window.open(url, '_blank', 'noopener,noreferrer');
    toast.success('LinkedIn composer opened!');
  };

  const handleDownloadNotebook = () => {
    if (!currentConcept) { toast.error('No concept selected'); return; }
    downloadNotebook(topic.id, currentConcept);
    toast.success('Downloading notebook…');
  };

  const handleDownloadImage = () => {
    if (!resolvedImageUrl) return;
    const a = document.createElement('a');
    a.href = resolvedImageUrl;
    a.download = `${currentConcept.toLowerCase().replace(/\s+/g, '_')}_byte.png`;
    a.target = '_blank';
    a.click();
    toast.success('Downloading image…');
  };

  return (
    <div className="space-y-6 max-w-2xl">
      {/* Header */}
      <div>
        <div className="flex items-center gap-3 mb-1">
          <span className="text-2xl">🚀</span>
          <h2 className="text-xl font-extrabold" style={{ color: 'var(--text-1)' }}>Share to LinkedIn</h2>
        </div>
        <p className="text-sm" style={{ color: 'var(--text-4)', marginLeft: 44 }}>
          Generate a compelling post from this byte.
        </p>
      </div>

      {/* Current byte summary */}
      <div className="rounded-2xl p-5" style={{ background: 'var(--accent-soft)', border: '1px solid var(--border)' }}>
        <div className="flex items-start gap-4">
          {resolvedImageUrl && (
            <div className="relative flex-shrink-0">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={resolvedImageUrl}
                alt=""
                className="w-20 h-20 rounded-xl object-cover"
                style={{ border: '1px solid var(--border)' }}
              />
              <button
                onClick={handleDownloadImage}
                title="Download image"
                className="absolute -bottom-2 -right-2 w-6 h-6 rounded-full flex items-center justify-center text-xs transition-all hover:scale-110"
                style={{
                  background: 'var(--accent)',
                  color: '#fff',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
                }}
              >
                ↓
              </button>
            </div>
          )}
          <div className="flex-1 min-w-0">
            <p className="text-xs font-bold uppercase tracking-widest mb-1" style={{ color: 'var(--text-5)', letterSpacing: '0.12em' }}>
              {topic.name}
            </p>
            <h3 className="text-sm font-bold mb-2" style={{ color: 'var(--text-1)' }}>{currentConcept}</h3>
            {byteAnalogy && (
              <p className="text-xs leading-relaxed italic" style={{ color: 'var(--text-3)' }}>
                &ldquo;{byteAnalogy.slice(0, 120)}{byteAnalogy.length > 120 ? '…' : ''}&rdquo;
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Custom angle */}
      <div>
        <label className="block text-xs font-bold uppercase tracking-widest mb-2" style={{ color: 'var(--text-4)', letterSpacing: '0.1em' }}>
          Custom Angle <span style={{ fontWeight: 400, textTransform: 'none', letterSpacing: 0 }}>(optional)</span>
        </label>
        <input
          value={customMessage}
          onChange={(e) => setCustomMessage(e.target.value)}
          placeholder={`e.g. "Focus on ${currentConcept} for junior ML engineers"`}
          className="w-full rounded-xl px-4 py-3 text-sm outline-none transition-colors"
          style={{
            background: 'var(--bg-2)',
            border: '1px solid var(--border-strong)',
            color: 'var(--text-1)',
          }}
          onFocus={(e) => (e.target.style.borderColor = 'rgba(139,92,246,0.5)')}
          onBlur={(e) => (e.target.style.borderColor = 'var(--border-strong)')}
        />
      </div>

      {/* Action buttons row */}
      <div className="flex flex-col gap-3">
        {/* Generate post */}
        <button
          onClick={handleGenerate}
          disabled={loading}
          className="w-full py-4 rounded-xl font-bold text-white transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 text-sm"
          style={{
            background: loading
              ? 'rgba(139,92,246,0.4)'
              : 'linear-gradient(135deg, #8b5cf6 0%, #22d3ee 100%)',
            boxShadow: loading ? 'none' : '0 4px 24px rgba(139,92,246,0.4)',
          }}
        >
          {loading ? (
            <>
              <span
                className="w-4 h-4 rounded-full border-2 animate-spin"
                style={{ borderColor: 'rgba(255,255,255,0.4)', borderTopColor: 'white' }}
              />
              Generating LinkedIn Post...
            </>
          ) : (
            <>{'\uD83D\uDE80'} Generate LinkedIn Post</>
          )}
        </button>

        {/* Download notebook */}
        <button
          onClick={handleDownloadNotebook}
          className="w-full py-3 rounded-xl font-bold transition-all duration-200 flex items-center justify-center gap-2 text-sm"
          style={{
            background: 'rgba(16,185,129,0.08)',
            border: '1px solid rgba(16,185,129,0.2)',
            color: '#34d399',
          }}
        >
          📓 Download Notebook
        </button>
      </div>

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
            className="space-y-5"
          >
            <div className="relative">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-bold uppercase tracking-widest" style={{ color: 'var(--text-4)', letterSpacing: '0.1em' }}>
                  LinkedIn Post
                </span>
                <button
                  onClick={handleCopy}
                  className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 hover:scale-105"
                  style={{
                    background: copied ? 'rgba(34,211,238,0.15)' : 'rgba(139,92,246,0.15)',
                    color: copied ? '#22d3ee' : '#8b5cf6',
                    border: copied ? '1px solid rgba(34,211,238,0.35)' : '1px solid rgba(139,92,246,0.35)',
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
                value={editablePost}
                onChange={(e) => setEditablePost(e.target.value)}
                rows={13}
                className="w-full rounded-xl px-5 py-4 text-sm resize-none outline-none"
                style={{
                  background: 'var(--bg-2)',
                  border: '1px solid var(--border)',
                  color: 'var(--text-2)',
                  fontFamily: 'Inter, sans-serif',
                  lineHeight: 1.7,
                }}
                onFocus={(e) => (e.target.style.borderColor = 'rgba(139,92,246,0.4)')}
                onBlur={(e) => (e.target.style.borderColor = 'var(--border)')}
              />
              <p className="text-xs mt-1.5" style={{ color: 'var(--text-5)' }}>
                Edit before posting — changes are local only.
              </p>
            </div>

            {/* Post to LinkedIn */}
            <button
              onClick={handlePostToLinkedIn}
              className="w-full py-4 rounded-xl font-bold transition-all duration-200 flex items-center justify-center gap-2.5 text-sm hover:scale-[1.01]"
              style={{
                background: 'linear-gradient(135deg, #0077b5 0%, #00a0dc 100%)',
                boxShadow: '0 4px 20px rgba(0,119,181,0.35)',
                color: '#fff',
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
              </svg>
              Post to LinkedIn
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
