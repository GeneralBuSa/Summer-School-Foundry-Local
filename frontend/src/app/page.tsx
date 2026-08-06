"use client";

import React, { useState, useRef } from "react";
import { Header } from "@/components/Header";
import { Sidebar } from "@/components/Sidebar";
import { ChatInput } from "@/components/ChatInput";
import { BookOpen, User, Bot, AlertCircle, ChevronDown, ChevronUp } from "lucide-react";

interface Source {
  source: string;
  chunk: number;
  score: number;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
}

const API_BASE = "http://localhost:8000";

export default function Home() {
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  };

  // Arama Ayarları State
  const [topK, setTopK] = useState(3);
  const [minScore, setMinScore] = useState(0.35);
  const [alpha, setAlpha] = useState(0.7);

  // AbortController referansı
  const abortControllerRef = useRef<AbortController | null>(null);

  // Kaynaklar expander açık/kapalı state (message.id -> boolean)
  const [openSources, setOpenSources] = useState<Record<string, boolean>>({});

  const toggleSources = (id: string) => {
    setOpenSources((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleSend = async (question: string) => {
    const userMsgId = Date.now().toString();
    const userMsg: Message = { id: userMsgId, role: "user", content: question };

    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setIsGenerating(true);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const history = messages.map((m) => ({ role: m.role, content: m.content }));
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question,
          chat_history: history,
          top_k: topK,
          min_similarity_score: minScore,
          alpha,
        }),
        signal: controller.signal,
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({ detail: "Sunucu yanıt vermedi." }));
        throw new Error(errData.detail || "İşlem sırasında hata oluştu.");
      }

      const data = await res.json();
      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: data.text,
        sources: data.sources,
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      if (err.name === "AbortError") {
        // İptal edildi: Son cevapsız kullanıcı mesajını temizle
        setMessages((prev) => prev.filter((m) => m.id !== userMsgId));
      } else {
        const errorMsg: Message = {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: `⚠️ Hata: ${err.message}`,
        };
        setMessages((prev) => [...prev, errorMsg]);
      }
    } finally {
      setIsGenerating(false);
      abortControllerRef.current = null;
    }
  };

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  };

  const handleClearChat = () => {
    if (isGenerating && abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setMessages([]);
  };

  return (
    <div className={`flex h-screen w-screen overflow-hidden transition-colors ${
      theme === "dark" ? "bg-black text-zinc-100" : "bg-slate-50 text-zinc-900"
    }`}>
      {/* Sol Sidebar */}
      <Sidebar
        topK={topK}
        setTopK={setTopK}
        minScore={minScore}
        setMinScore={setMinScore}
        alpha={alpha}
        setAlpha={setAlpha}
        isGenerating={isGenerating}
        messages={messages}
        apiBase={API_BASE}
        theme={theme}
      />

      {/* Sağ Ana Sohbet Alanı */}
      <div className={`flex-1 flex flex-col h-full overflow-hidden relative ${
        theme === "dark" ? "bg-black" : "bg-white"
      }`}>
        <Header
          onClearChat={handleClearChat}
          hasMessages={messages.length > 0}
          theme={theme}
          onToggleTheme={toggleTheme}
        />

        {/* Mesaj Listesi */}
        <main className="flex-1 overflow-y-auto p-6 flex flex-col gap-6 max-w-4xl mx-auto w-full">
          {messages.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center text-center gap-3 my-auto py-20 text-zinc-400">
              <Bot className={`w-12 h-12 stroke-[1.5] ${theme === "dark" ? "text-zinc-800" : "text-zinc-300"}`} />
              <h2 className={`text-lg font-medium ${theme === "dark" ? "text-zinc-300" : "text-zinc-700"}`}>
                Nasılsınız? Bugün hangi dokümanı incelemek istersiniz?
              </h2>
              <p className="text-xs max-w-md">
                Dokümanlarınızı yan panelden yükleyip indeksleyebilir ve doğrudan sorular sorabilirsiniz.
              </p>
            </div>
          ) : (
            messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-3 text-sm leading-relaxed ${
                  msg.role === "user" ? "justify-end" : "justify-start"
                }`}
              >
                {msg.role === "assistant" && (
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5 ${
                    theme === "dark"
                      ? "bg-rose-950/60 border border-rose-800/40 text-rose-400"
                      : "bg-rose-100 border border-rose-200 text-rose-600"
                  }`}>
                    <Bot className="w-4 h-4" />
                  </div>
                )}

                <div
                  className={`flex flex-col gap-2 max-w-[80%] ${
                    msg.role === "user"
                      ? theme === "dark"
                        ? "bg-rose-900/80 border border-rose-800/60 text-rose-100 rounded-2xl rounded-tr-none px-4 py-3 shadow-lg"
                        : "bg-rose-600 border border-rose-500 text-white rounded-2xl rounded-tr-none px-4 py-3 shadow-md"
                      : theme === "dark"
                      ? "bg-zinc-950 border border-zinc-900 text-zinc-200 rounded-2xl rounded-tl-none px-4 py-3 shadow-md"
                      : "bg-zinc-100 border border-zinc-200 text-zinc-800 rounded-2xl rounded-tl-none px-4 py-3 shadow-sm"
                  }`}
                >
                  <p className="whitespace-pre-wrap">{msg.content}</p>

                  {/* Kaynaklar Accordion */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className={`mt-2 border-t pt-2 ${theme === "dark" ? "border-zinc-900" : "border-zinc-200"}`}>
                      <button
                        onClick={() => toggleSources(msg.id)}
                        className={`flex items-center gap-1.5 text-xs font-medium transition-colors ${
                          theme === "dark" ? "text-zinc-400 hover:text-zinc-200" : "text-zinc-600 hover:text-zinc-900"
                        }`}
                      >
                        <BookOpen className="w-3.5 h-3.5" />
                        <span>Kullanılan Kaynaklar</span>
                        {openSources[msg.id] ? (
                          <ChevronUp className="w-3.5 h-3.5" />
                        ) : (
                          <ChevronDown className="w-3.5 h-3.5" />
                        )}
                      </button>

                      {openSources[msg.id] && (
                        <ul className={`mt-2 flex flex-col gap-1 text-xs pl-2 border-l ${
                          theme === "dark" ? "text-zinc-400 border-zinc-800" : "text-zinc-600 border-zinc-300"
                        }`}>
                          {msg.sources.map((s, idx) => (
                            <li key={idx}>
                              • <strong className={theme === "dark" ? "text-zinc-300" : "text-zinc-800"}>{s.source}</strong> (Parça {s.chunk}, Benzerlik:{" "}
                              <code className={`px-1 py-0.5 rounded border ${
                                theme === "dark"
                                  ? "bg-black text-rose-400 border-zinc-800"
                                  : "bg-zinc-200 text-rose-700 border-zinc-300"
                              }`}>{s.score.toFixed(2)}</code>)
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}
                </div>

                {msg.role === "user" && (
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5 ${
                    theme === "dark"
                      ? "bg-zinc-900 border border-zinc-800 text-zinc-300"
                      : "bg-zinc-200 border border-zinc-300 text-zinc-700"
                  }`}>
                    <User className="w-4 h-4" />
                  </div>
                )}
              </div>
            ))
          )}

          {/* Yanıt Üretiliyor Yükleme Göstergesi */}
          {isGenerating && (
            <div className={`flex items-center gap-3 text-sm animate-pulse ${theme === "dark" ? "text-zinc-400" : "text-zinc-600"}`}>
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                theme === "dark"
                  ? "bg-rose-950/60 border border-rose-800/40 text-rose-400"
                  : "bg-rose-100 border border-rose-200 text-rose-600"
              }`}>
                <Bot className="w-4 h-4 animate-spin" />
              </div>
              <span>Yanıt üretiliyor...</span>
            </div>
          )}
        </main>

        {/* Alt Sohbet Çubuğu */}
        <div className={`p-4 backdrop-blur-md border-t transition-colors ${
          theme === "dark"
            ? "bg-black/90 border-zinc-900"
            : "bg-white/90 border-zinc-200"
        }`}>
          <ChatInput onSend={handleSend} onStop={handleStop} isGenerating={isGenerating} theme={theme} />
        </div>
      </div>
    </div>
  );
}
