'use client';

import { useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import { useChatStore } from '@/src/store/chatStore';
import type { ChatSource } from '@/src/store/chatStore';

const ChatBubble = dynamic(() => import('@/src/components/chat/ChatBubble'), { ssr: false });
const ChatInput = dynamic(() => import('@/src/components/chat/ChatInput'), { ssr: false });
const FloatingParticles = dynamic(() => import('@/src/components/chat/FloatingParticles'), { ssr: false });

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

export default function ChatPage() {
  const {
    messages, isStreaming, conversationId,
    addMessage, appendToken, pushStep, setMsgSources, finishMessage, clearHistory,
  } = useChatStore();

  const bottomRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length, isStreaming]);

  const sendMessage = useCallback(async (text: string) => {
    if (isStreaming) return;

    const userMsgId = crypto.randomUUID();
    addMessage({ id: userMsgId, role: 'user', content: text, timestamp: Date.now() });

    const assistantId = crypto.randomUUID();
    addMessage({ id: assistantId, role: 'assistant', content: '', streaming: true, steps: [], timestamp: Date.now() });

    // Build history for context (exclude the just-added assistant placeholder)
    const history = messages.slice(-12).map((m) => ({ role: m.role, content: m.content }));

    try {
      const res = await fetch(`${API_URL}/api/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, history, conversation_id: conversationId }),
      });

      if (!res.ok || !res.body) throw new Error(`API error ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const raw = line.slice(6).trim();
          if (!raw) continue;
          try {
            const evt = JSON.parse(raw) as {
              type: 'step' | 'token' | 'sources' | 'done';
              content?: string;
              sources?: ChatSource[];
            };
            if (evt.type === 'step' && evt.content) {
              pushStep(assistantId, evt.content);
            } else if (evt.type === 'token' && evt.content) {
              appendToken(assistantId, evt.content);
            } else if (evt.type === 'sources' && evt.sources) {
              setMsgSources(assistantId, evt.sources);
            } else if (evt.type === 'done') {
              finishMessage(assistantId);
            }
          } catch {
            // skip malformed
          }
        }
      }
      finishMessage(assistantId);
    } catch (err) {
      appendToken(assistantId, '\n\n⚠️ Could not reach the API server. Make sure `uv run python api_server.py` is running.');
      finishMessage(assistantId);
    }
  }, [isStreaming, messages, conversationId, addMessage, appendToken, pushStep, setMsgSources, finishMessage]);

  const isEmpty = messages.length === 0;

  return (
    <div className="flex flex-col h-screen overflow-hidden relative" style={{ background: '#0a0a0f' }}>
      {/* Ambient background */}
      <div className="fixed inset-0 pointer-events-none" style={{ zIndex: 0 }}>
        <div className="absolute top-0 right-1/4 w-[500px] h-[500px] rounded-full opacity-5"
          style={{ background: 'radial-gradient(circle, #8b5cf6, transparent 70%)', filter: 'blur(80px)' }} />
        <div className="absolute bottom-1/4 left-1/4 w-[400px] h-[400px] rounded-full opacity-5"
          style={{ background: 'radial-gradient(circle, #22d3ee, transparent 70%)', filter: 'blur(80px)' }} />
      </div>
      <FloatingParticles />

      {/* Nav */}
      <nav className="relative z-20 flex items-center justify-between px-5 py-3 flex-shrink-0"
        style={{ borderBottom: '1px solid rgba(139,92,246,0.12)', backdropFilter: 'blur(12px)', background: 'rgba(10,10,15,0.8)' }}>
        <div className="flex items-center gap-4">
          <Link href="/" className="flex items-center gap-2 group">
            <span className="text-xl">⚡</span>
            <span className="font-extrabold text-sm hidden sm:block" style={{ color: '#8b5cf6' }}>Zizi Byte</span>
          </Link>
          <div className="flex items-center gap-1">
            {[{ href: '/', label: 'Galaxy' }, { href: '/learn', label: 'Learn' }, { href: '/chat', label: 'Chat', active: true }].map((n) => (
              <Link key={n.href} href={n.href}
                className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200"
                style={n.active
                  ? { background: 'rgba(139,92,246,0.2)', color: '#c4b5fd', border: '1px solid rgba(139,92,246,0.35)' }
                  : { color: '#64748b', border: '1px solid transparent' }
                }>
                {n.label}
              </Link>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 text-xs" style={{ color: '#475569' }}>
            <motion.span
              animate={{ opacity: [0.4, 1, 0.4] }}
              transition={{ duration: 2, repeat: Infinity }}
              className="w-1.5 h-1.5 rounded-full"
              style={{ background: '#22d3ee', display: 'inline-block' }}
            />
            KG+Dense · Cohere
          </div>
          {messages.length > 0 && (
            <button onClick={clearHistory}
              className="px-2 py-1 rounded-lg text-xs transition-colors"
              style={{ color: '#475569', border: '1px solid rgba(255,255,255,0.06)' }}
              onMouseEnter={(e) => (e.currentTarget.style.color = '#f87171')}
              onMouseLeave={(e) => (e.currentTarget.style.color = '#475569')}>
              Clear
            </button>
          )}
        </div>
      </nav>

      {/* Messages area */}
      <div ref={scrollRef} className="relative z-10 flex-1 overflow-y-auto px-4 py-6" style={{ scrollbarWidth: 'thin' }}>
        <div className="max-w-2xl mx-auto space-y-6">
          {/* Empty state */}
          <AnimatePresence>
            {isEmpty && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="flex flex-col items-center justify-center text-center pt-16 pb-8 gap-6"
              >
                {/* Animated logo */}
                <motion.div
                  animate={{ rotate: [0, 5, -5, 0], scale: [1, 1.05, 1] }}
                  transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
                  className="w-20 h-20 rounded-2xl flex items-center justify-center text-4xl relative"
                  style={{ background: 'linear-gradient(135deg, rgba(139,92,246,0.2), rgba(34,211,238,0.1))',
                    border: '1px solid rgba(139,92,246,0.3)', boxShadow: '0 0 40px rgba(139,92,246,0.2)' }}
                >
                  ⚡
                  {/* Orbit ring */}
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 8, repeat: Infinity, ease: 'linear' }}
                    className="absolute inset-0 rounded-2xl"
                    style={{ border: '1px solid rgba(139,92,246,0.3)', borderTopColor: 'transparent',
                      borderRightColor: 'transparent' }}
                  />
                </motion.div>

                <div>
                  <h2 className="text-2xl font-bold mb-1" style={{ color: '#f1f5f9' }}>Ask Zizi anything</h2>
                  <p className="text-sm" style={{ color: '#64748b' }}>
                    Grounded in your course knowledge base · Analogy-first · Cited sources
                  </p>
                </div>

                {/* Capability badges */}
                <div className="flex flex-wrap gap-2 justify-center">
                  {[
                    { icon: '🧠', label: 'KG+Dense Retrieval' },
                    { icon: '🎯', label: 'Cohere Reranked' },
                    { icon: '💡', label: 'Analogy-First' },
                    { icon: '📚', label: 'Cited Sources' },
                    { icon: '🔁', label: 'Conversation Memory' },
                  ].map(({ icon, label }) => (
                    <motion.span
                      key={label}
                      whileHover={{ scale: 1.05, borderColor: 'rgba(139,92,246,0.5)' }}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs"
                      style={{ background: 'rgba(139,92,246,0.07)', border: '1px solid rgba(139,92,246,0.18)', color: '#94a3b8' }}
                    >
                      {icon} {label}
                    </motion.span>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Messages */}
          {messages.map((msg) => (
            <ChatBubble key={msg.id} msg={msg} />
          ))}

          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input area */}
      <div className="relative z-20 flex-shrink-0 px-4 pb-4 pt-2"
        style={{ borderTop: '1px solid rgba(139,92,246,0.1)', backdropFilter: 'blur(12px)', background: 'rgba(10,10,15,0.85)' }}>
        <div className="max-w-2xl mx-auto">
          <ChatInput onSend={sendMessage} disabled={isStreaming} />
        </div>
      </div>
    </div>
  );
}
