"use client";

/**
 * Üst Başlık (Header) Bileşeni
 *
 * Uygulamanın başlığını, alt bilgisini, tema değiştirme (Dark/Light) butonunu
 * ve sohbet geçmişini temizleme onay pop-up modal ekranını barındırır.
 */

import React, { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { Trash2, Bot, Sun, Moon, AlertTriangle } from "lucide-react";

/** Header bileşeni prop parametreleri */
interface HeaderProps {
  /** Sohbet geçmişini temizleyen işlev */
  onClearChat: () => void;
  /** Ekran aktif mesaj içeriyor mu bilgisi */
  hasMessages: boolean;
  /** Aktif tema modu ("dark" | "light") */
  theme: "dark" | "light";
  /** Temalar arası geçiş yaptıran tetikleyici fonksiyon */
  onToggleTheme: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  onClearChat,
  hasMessages,
  theme,
  onToggleTheme,
}) => {
  // Temizleme onay modalı ve hydration kontrol state'leri
  const [showConfirm, setShowConfirm] = useState(false);
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  return (
    <>
      <header className={`h-14 border-b transition-colors px-6 flex items-center justify-between sticky top-0 z-40 ${
        theme === "dark"
          ? "border-zinc-900 bg-black/90 text-zinc-100"
          : "border-zinc-200 bg-white/90 text-zinc-900"
      } backdrop-blur-md`}>
        {/* Sol Logo ve Başlık Bilgisi */}
        <div className="flex items-center gap-3">
          <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
            theme === "dark"
              ? "bg-rose-950/60 border border-rose-800/40 text-rose-400"
              : "bg-rose-100 border border-rose-200 text-rose-600"
          }`}>
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <h1 className="font-semibold text-base leading-tight">
              Yerel RAG Belge Asistanı
            </h1>
            <p className={`text-xs ${theme === "dark" ? "text-zinc-400" : "text-zinc-500"}`}>
              Dokümanlarınızı yerelde indeksleyin, güvenle Türkçe yanıtlar alın.
            </p>
          </div>
        </div>

        {/* Sağ Buton Grubu: Tema ve Temizle */}
        <div className="flex items-center gap-2">
          <button
            onClick={onToggleTheme}
            title={theme === "dark" ? "Açık temaya geç" : "Koyu temaya geç"}
            className={`p-2 rounded-lg border transition-all flex items-center justify-center ${
              theme === "dark"
                ? "border-zinc-800 bg-zinc-900 text-amber-400 hover:bg-zinc-800"
                : "border-zinc-200 bg-zinc-100 text-indigo-600 hover:bg-zinc-200"
            }`}
          >
            {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>

          {hasMessages && (
            <button
              onClick={() => setShowConfirm(true)}
              title="Sohbet geçmişini temizle"
              className={`p-2 rounded-lg border transition-all flex items-center justify-center ${
                theme === "dark"
                  ? "border-zinc-800 bg-zinc-900 hover:bg-rose-950/40 hover:border-rose-800/50 hover:text-rose-400 text-zinc-300"
                  : "border-zinc-200 bg-zinc-100 hover:bg-rose-50 hover:border-rose-300 hover:text-rose-600 text-zinc-700"
              }`}
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
        </div>
      </header>

      {/* Silme Onay Modal Pop-up (React Portal ile iletilir) */}
      {showConfirm && isMounted && createPortal(
        <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className={`w-full max-w-sm p-5 rounded-2xl border shadow-2xl transition-all ${
            theme === "dark"
              ? "bg-zinc-950 border-zinc-800 text-zinc-100"
              : "bg-white border-zinc-200 text-zinc-900"
          }`}>
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-500 flex items-center justify-center shrink-0">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-semibold text-sm">Sohbeti Temizle</h3>
                <p className={`text-xs ${theme === "dark" ? "text-zinc-400" : "text-zinc-500"}`}>
                  Tüm sohbet geçmişini silmek istediğinize emin misiniz?
                </p>
              </div>
            </div>
            <div className="flex items-center justify-end gap-2.5 mt-5">
              <button
                onClick={() => setShowConfirm(false)}
                className={`px-3.5 py-1.5 rounded-xl border text-xs font-medium transition-colors ${
                  theme === "dark"
                    ? "border-zinc-800 bg-zinc-900 hover:bg-zinc-800 text-zinc-300"
                    : "border-zinc-300 bg-zinc-100 hover:bg-zinc-200 text-zinc-700"
                }`}
              >
                Vazgeç
              </button>
              <button
                onClick={() => {
                  onClearChat();
                  setShowConfirm(false);
                }}
                className="px-3.5 py-1.5 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-medium transition-colors shadow-sm"
              >
                Evet, Sil
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}
    </>
  );
};

