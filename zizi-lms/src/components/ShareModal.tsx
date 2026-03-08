'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import toast from 'react-hot-toast';
import { createSharePost } from '@/src/lib/api';
import type { TopicSummary } from '@/src/types';

interface Props {
  topic: TopicSummary;
}

export default function ShareModal({ topic }: Props) {
  const [loading, setLoading] = useState(false);
  const [post, setPost] = useState('');
  const [imageUrl, setImageUrl] = useState('');
  const [isDuplicate, setIsDuplicate] = useState(false);
  const [duplicateReason, setDuplicateReason] = useState('');
  const [customMessage, setCustomMessage] = useState('');

  const handleGenerate = async () => {
    setLoading(true);
    setPost('');
    setImageUrl('');
    setIsDuplicate(false);
    try {
      const result = await createSharePost(topic.id, customMessage);
      if ((result as any).is_duplicate) {
        setIsDuplicate(true);
        setDuplicateReason((result as any).reason || 'This topic was already posted.');
      } else {
        setPost((result as any).post || '');
        setImageUrl((result as any).image_url || '');
        toast.success('Post generated!');
      }
    } catch (err) {
      toast.error('Failed to generate post — check the API server.');
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(post);
    toast.success('Copied to clipboard!');
  };

  return (
    <div className="space-y-6 max-w-2xl mx-auto">
      {/* Topic summary */}
      <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
        <h3 className="text-lg font-semibold text-white mb-1">{topic.name}</h3>
        <p className="text-sm text-gray-400 mb-3">{topic.description}</p>
        <div className="flex flex-wrap gap-2">
          {topic.concepts.map((c) => (
            <span
              key={c}
              className="px-2 py-0.5 rounded-full bg-purple-600/20 text-purple-300 text-xs border border-purple-500/30"
            >
              {c}
            </span>
          ))}
        </div>
      </div>

      {/* Custom message input */}
      <div>
        <label className="block text-sm text-gray-400 mb-1">
          Custom angle (optional)
        </label>
        <input
          value={customMessage}
          onChange={(e) => setCustomMessage(e.target.value)}
          placeholder={`e.g. "Explain ${topic.name} for beginner ML engineers"`}
          className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-purple-500/50"
        />
      </div>

      <button
        onClick={handleGenerate}
        disabled={loading}
        className="w-full py-3 rounded-xl font-semibold text-white bg-gradient-to-r from-purple-600 to-cyan-600 hover:opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? '✨ Generating LinkedIn Post...' : '🚀 Generate LinkedIn Post'}
      </button>

      <AnimatePresence>
        {isDuplicate && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="rounded-xl border border-yellow-500/30 bg-yellow-500/10 p-4 text-yellow-300 text-sm"
          >
            ⚠️ {duplicateReason}
          </motion.div>
        )}

        {post && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-4"
          >
            <div className="relative">
              <textarea
                readOnly
                value={post}
                rows={10}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-gray-200 resize-none focus:outline-none"
              />
              <button
                onClick={handleCopy}
                className="absolute top-3 right-3 text-xs text-purple-400 hover:text-purple-300 bg-white/10 px-2 py-1 rounded-lg"
              >
                Copy
              </button>
            </div>

            {imageUrl && (
              <div>
                <p className="text-xs text-gray-500 mb-2">Generated poster</p>
                <img
                  src={imageUrl}
                  alt="Generated poster"
                  className="w-full rounded-xl border border-white/10"
                />
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
