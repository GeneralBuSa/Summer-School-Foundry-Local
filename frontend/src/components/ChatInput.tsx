"use client";

/**
 * Sohbet Girdi Kutusu (ChatInput Component)
 *
 * Kullanıcının sorularını yazıp gönderebildiği, uzunluğuna göre otomatik genişleyen textarea
 * ve yanıt üretimi esnasında durdurma (Stop) onay popup modalını barındıran bileşen.
 */

import React, { useState, useRef, useEffect } from "react";
import { createPortal } from "react-dom";
import { ArrowUp, Square, AlertTriangle } from "lucide-react";

/** ChatInput bileşeni prop arayüzü */
interface ChatInputProps {
  /** Soru gönderme işlevi */
  onSend: (message: string) => void;
  /** Yanıt üretimini durdurma işlevi */
  onStop: () => void;
  /** Yanıt üretilme durumu (loading) */
  isGenerating: boolean;
  /** Tema modu ("dark" | "light") */
  theme?: "dark" | "light";
}

export const ChatInput: React.FC<ChatInputProps> = ({ onSend, onStop, isGenerating, theme = "dark" }) => {
  const [input, setInput] = useState("");
  const [showStopConfirm, setShowStopConfirm] = useState(false);
  const [isMounted, setIsMounted] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  // Girdi metni geliştikçe textarea yüksekliğini dinamik olarak ayarla
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 140)}px`;
    }
  }, [input]);

  /** Form gönderildiğinde tetiklenen işleyici */
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isGenerating) return;
    onSend(input.trim());
    setInput("");
  };

  /** Enter tuşuna basıldığında (Shift+Enter hariç) formu gönderir */
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <>
      <form
        onSubmit={handleSubmit}
        className={`relative max-w-4xl mx-auto w-full border rounded-2xl p-2 shadow-lg transition-all flex items-end gap-2 ${
          theme === "dark"
            ? "bg-zinc-950 border-zinc-800/80 focus-within:border-zinc-700 shadow-2xl"
            : "bg-white border-zinc-300 focus-within:border-rose-500/50 shadow-md"
        }`}
      >
        {/* Metin Giriş Alanı */}
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Belgeleriniz hakkında soru sorun..."
          rows={1}
          disabled={isGenerating}
          className={`w-full bg-transparent text-sm px-3 py-2 focus:outline-none resize-none disabled:opacity-60 max-h-36 ${
            theme === "dark"
              ? "text-zinc-100 placeholder-zinc-500"
              : "text-zinc-900 placeholder-zinc-400"
          }`}
        />

        {/* Gönder / Durdur Butonu */}
        {isGenerating ? (
          <button
            type="button"
            onClick={() => setShowStopConfirm(true)}
            title="Yanıt üretimini durdur"
            className="w-8 h-8 rounded-lg bg-rose-800 hover:bg-rose-700 text-white flex items-center justify-center shrink-0 transition-all shadow-md active:scale-95 animate-pulse"
          >
            <Square className="w-4 h-4 fill-current" />
          </button>
        ) : (
          <button
            type="submit"
            disabled={!input.trim()}
            title="Gönder"
            className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 transition-all active:scale-95 ${
              theme === "dark"
                ? "bg-zinc-800 hover:bg-zinc-700 disabled:opacity-30 text-zinc-200"
                : "bg-rose-600 hover:bg-rose-700 disabled:opacity-30 text-white"
            }`}
          >
            <ArrowUp className="w-4 h-4" />
          </button>
        )}
      </form>

      {/* İptal Etme Onay Pop-up Modal (createPortal ile gövdeye sabitlendi) */}
      {showStopConfirm && isMounted && createPortal(
        <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className={`w-full max-w-sm p-5 rounded-2xl border shadow-2xl transition-all ${
            theme === "dark"
              ? "bg-zinc-950 border-zinc-800 text-zinc-100"
              : "bg-white border-zinc-200 text-zinc-900"
          }`}>
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-500 flex items-center justify-center shrink-0">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-semibold text-sm">Yanıtı İptal Et</h3>
                <p className={`text-xs ${theme === "dark" ? "text-zinc-400" : "text-zinc-500"}`}>
                  Devam eden yanıt üretimini durdurmak istediğinize emin misiniz?
                </p>
              </div>
            </div>
            <div className="flex items-center justify-end gap-2.5 mt-5">
              <button
                onClick={() => setShowStopConfirm(false)}
                className={`px-3.5 py-1.5 rounded-xl border text-xs font-medium transition-colors ${
                  theme === "dark"
                    ? "border-zinc-800 bg-zinc-900 hover:bg-zinc-800 text-zinc-300"
                    : "border-zinc-300 bg-zinc-100 hover:bg-zinc-200 text-zinc-700"
                }`}
              >
                Devam Et
              </button>
              <button
                onClick={() => {
                  onStop();
                  setShowStopConfirm(false);
                }}
                className="px-3.5 py-1.5 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-medium transition-colors shadow-sm"
              >
                Evet, Durdur
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}
    </>
  );
};

