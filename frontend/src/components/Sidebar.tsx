"use client";

import React, { useState, useEffect, useRef } from "react";
import { Upload, RefreshCw, Sliders, Eye, FileText, Download, X, ChevronDown } from "lucide-react";

interface SidebarProps {
  topK: number;
  setTopK: (v: number) => void;
  minScore: number;
  setMinScore: (v: number) => void;
  alpha: number;
  setAlpha: (v: number) => void;
  isGenerating: boolean;
  messages: Array<{ role: string; content: string; sources?: any[] }>;
  apiBase: string;
  theme?: "dark" | "light";
}

export const Sidebar: React.FC<SidebarProps> = ({
  topK,
  setTopK,
  minScore,
  setMinScore,
  alpha,
  setAlpha,
  isGenerating,
  messages,
  apiBase,
  theme = "dark",
}) => {
  const [documents, setDocuments] = useState<string[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<string>("");
  const [previewContent, setPreviewContent] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isIngesting, setIsIngesting] = useState(false);
  const [statusMsg, setStatusMsg] = useState<{ type: "success" | "error" | "info"; text: string } | null>(null);
  const [isSelectOpen, setIsSelectOpen] = useState(false);
  const selectRef = useRef<HTMLDivElement>(null);

  const [width, setWidth] = useState(320);
  const [isResizing, setIsResizing] = useState(false);

  const startResizing = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return;
      const newWidth = Math.min(Math.max(e.clientX, 220), 540);
      setWidth(newWidth);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    if (isResizing) {
      window.addEventListener("mousemove", handleMouseMove);
      window.addEventListener("mouseup", handleMouseUp);
    }

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isResizing]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (selectRef.current && !selectRef.current.contains(event.target as Node)) {
        setIsSelectOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const getFileIcon = (filename: string) => {
    const ext = filename.split(".").pop()?.toLowerCase();
    if (ext === "pdf") return <FileText className="w-3.5 h-3.5 text-rose-500 shrink-0" />;
    if (ext === "docx" || ext === "doc") return <FileText className="w-3.5 h-3.5 text-blue-500 shrink-0" />;
    if (ext === "xlsx" || ext === "csv") return <FileText className="w-3.5 h-3.5 text-emerald-500 shrink-0" />;
    if (ext === "md" || ext === "txt") return <FileText className="w-3.5 h-3.5 text-amber-500 shrink-0" />;
    return <FileText className="w-3.5 h-3.5 text-zinc-400 shrink-0" />;
  };

  const fetchDocuments = async () => {
    try {
      const res = await fetch(`${apiBase}/api/documents`);
      if (res.ok) {
        const data = await res.json();
        setDocuments(data.documents || []);
        if (data.documents && data.documents.length > 0 && !selectedDoc) {
          setSelectedDoc(data.documents[0]);
        }
      }
    } catch {
      // Ignored
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    setIsUploading(true);
    setStatusMsg(null);

    const formData = new FormData();
    for (let i = 0; i < e.target.files.length; i++) {
      formData.append("files", e.target.files[i]);
    }

    try {
      const res = await fetch(`${apiBase}/api/upload`, {
        method: "POST",
        body: formData,
      });
      if (res.ok) {
        const data = await res.json();
        setStatusMsg({ type: "success", text: data.message });
        await fetchDocuments();
      } else {
        setStatusMsg({ type: "error", text: "Yükleme hatası oluştu." });
      }
    } catch (err: any) {
      setStatusMsg({ type: "error", text: `Yükleme hatası: ${err.message}` });
    } finally {
      setIsUploading(false);
    }
  };

  const handleIngest = async () => {
    setIsIngesting(true);
    setStatusMsg({ type: "info", text: "İndeksleme yapılıyor..." });

    try {
      const res = await fetch(`${apiBase}/api/ingest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ force_reindex: false }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.indexed_documents > 0) {
          setStatusMsg({
            type: "success",
            text: `İndekslendi: ${data.indexed_documents} yeni/güncellenen belge (${data.chunk_count} parça).`,
          });
        } else {
          setStatusMsg({ type: "info", text: "Bilgi tabanı güncel, yeni belge yok." });
        }
        await fetchDocuments();
      } else {
        setStatusMsg({ type: "error", text: "İndeksleme hatası oluştu." });
      }
    } catch (err: any) {
      setStatusMsg({ type: "error", text: `İndeksleme hatası: ${err.message}` });
    } finally {
      setIsIngesting(false);
    }
  };

  const handlePreview = async () => {
    if (!selectedDoc) return;
    try {
      const res = await fetch(`${apiBase}/api/preview?file_path=${encodeURIComponent(selectedDoc)}`);
      if (res.ok) {
        const data = await res.json();
        setPreviewContent(data.content);
      } else {
        setStatusMsg({ type: "error", text: "Belge okunamadı." });
      }
    } catch (err: any) {
      setStatusMsg({ type: "error", text: `Önizleme hatası: ${err.message}` });
    }
  };

  const handleDownloadReport = () => {
    let reportMd = "# Yerel RAG Sohbet Raporu\n\n";
    messages.forEach((m) => {
      const roleTitle = m.role === "user" ? "👤 Kullanıcı" : "🤖 Asistan";
      reportMd += `### ${roleTitle}\n${m.content}\n\n`;
      if (m.sources && m.sources.length > 0) {
        reportMd += "**Kullanılan Kaynaklar:**\n";
        m.sources.forEach((s) => {
          reportMd += `- ${s.source} (Parça ${s.chunk}, Skor: ${s.score.toFixed(2)})\n`;
        });
        reportMd += "\n";
      }
    });

    const blob = new Blob([reportMd], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "rag_sohbet_raporu.md";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <aside
      style={{ width: `${width}px` }}
      className={`relative border-r p-4 flex flex-col gap-6 overflow-y-auto shrink-0 text-sm transition-colors ${
        isResizing ? "select-none" : ""
      } ${
        theme === "dark"
          ? "border-zinc-900 bg-black/90 text-zinc-100"
          : "border-zinc-200 bg-slate-100/90 text-zinc-800"
      }`}
    >
      {/* Sürükleme Tutamacı (Resize Handle) */}
      <div
        onMouseDown={startResizing}
        className={`absolute top-0 right-0 w-1.5 h-full cursor-col-resize hover:bg-rose-500/50 active:bg-rose-500 transition-colors z-30 ${
          isResizing ? "bg-rose-500" : "bg-transparent hover:bg-rose-500/30"
        }`}
        title="Genişliği değiştirmek için sürükleyin"
      />
      {/* Belge Yönetimi */}
      <section className="flex flex-col gap-3">
        <h2 className={`font-semibold flex items-center gap-2 ${theme === "dark" ? "text-zinc-200" : "text-zinc-900"}`}>
          <Upload className="w-4 h-4 text-rose-500" />
          Belge Yönetimi
        </h2>

        <label className={`border border-dashed rounded-lg p-3 text-center cursor-pointer transition-all flex flex-col items-center gap-1 ${
          theme === "dark"
            ? "border-zinc-800 hover:border-zinc-600 bg-zinc-950/80"
            : "border-zinc-300 hover:border-zinc-400 bg-white/80"
        }`}>
          <Upload className="w-5 h-5 text-zinc-400" />
          <span className={`text-xs ${theme === "dark" ? "text-zinc-300" : "text-zinc-600"}`}>
            Yeni Belge Yükle (.md, .pdf, .docx...)
          </span>
          <input
            type="file"
            multiple
            accept=".md,.txt,.pdf,.docx,.xlsx,.csv"
            onChange={handleFileUpload}
            disabled={isUploading || isGenerating}
            className="hidden"
          />
        </label>

        <button
          onClick={handleIngest}
          disabled={isIngesting || isGenerating}
          className="w-full py-2 px-3 rounded-lg bg-rose-700 hover:bg-rose-600 disabled:opacity-50 text-white font-medium transition-all flex items-center justify-center gap-2 text-xs shadow-sm"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isIngesting ? "animate-spin" : ""}`} />
          Bilgi Tabanını İndeksle / Güncelle
        </button>

        {statusMsg && (
          <div
            className={`p-2.5 rounded-lg text-xs border ${
              statusMsg.type === "success"
                ? theme === "dark" ? "bg-emerald-950/40 border-emerald-800/50 text-emerald-400" : "bg-emerald-50 border-emerald-200 text-emerald-700"
                : statusMsg.type === "error"
                ? theme === "dark" ? "bg-rose-950/40 border-rose-800/50 text-rose-400" : "bg-rose-50 border-rose-200 text-rose-700"
                : theme === "dark" ? "bg-blue-950/40 border-blue-800/50 text-blue-400" : "bg-blue-50 border-blue-200 text-blue-700"
            }`}
          >
            {statusMsg.text}
          </div>
        )}
      </section>

      <hr className={theme === "dark" ? "border-zinc-900" : "border-zinc-200"} />

      {/* Arama Ayarları */}
      <section className="flex flex-col gap-3">
        <h2 className={`font-semibold flex items-center gap-2 text-xs uppercase tracking-wider ${
          theme === "dark" ? "text-zinc-400" : "text-zinc-500"
        }`}>
          <Sliders className="w-4 h-4 text-rose-500" />
          Arama Ayarları
        </h2>

        <div className="flex flex-col gap-2.5">
          {/* Top-K Card */}
          <div className={`flex flex-col gap-2 p-3 border rounded-xl transition-all shadow-sm ${
            theme === "dark" ? "bg-zinc-950 border-zinc-900 hover:border-zinc-800" : "bg-white border-zinc-200 hover:border-zinc-300"
          }`}>
            <div className="flex justify-between items-center text-xs">
              <span className={`font-medium ${theme === "dark" ? "text-zinc-300" : "text-zinc-700"}`}>Top-K Parça Sayısı</span>
              <span className={`px-2 py-0.5 rounded-md border font-mono text-xs font-semibold ${
                theme === "dark" ? "bg-rose-950/80 border-rose-800/50 text-rose-300" : "bg-rose-50 border-rose-200 text-rose-700"
              }`}>
                {topK}
              </span>
            </div>
            <input
              type="range"
              min={1}
              max={10}
              step={1}
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="w-full h-1.5 bg-zinc-700 accent-rose-600 rounded-lg appearance-none cursor-pointer"
            />
          </div>

          {/* Min Score Card */}
          <div className={`flex flex-col gap-2 p-3 border rounded-xl transition-all shadow-sm ${
            theme === "dark" ? "bg-zinc-950 border-zinc-900 hover:border-zinc-800" : "bg-white border-zinc-200 hover:border-zinc-300"
          }`}>
            <div className="flex justify-between items-center text-xs">
              <span className={`font-medium ${theme === "dark" ? "text-zinc-300" : "text-zinc-700"}`}>Min Benzerlik Eşiği</span>
              <span className={`px-2 py-0.5 rounded-md border font-mono text-xs font-semibold ${
                theme === "dark" ? "bg-rose-950/80 border-rose-800/50 text-rose-300" : "bg-rose-50 border-rose-200 text-rose-700"
              }`}>
                {minScore.toFixed(2)}
              </span>
            </div>
            <input
              type="range"
              min={0.0}
              max={1.0}
              step={0.05}
              value={minScore}
              onChange={(e) => setMinScore(Number(e.target.value))}
              className="w-full h-1.5 bg-zinc-700 accent-rose-600 rounded-lg appearance-none cursor-pointer"
            />
          </div>

          {/* Alpha Card */}
          <div className={`flex flex-col gap-2 p-3 border rounded-xl transition-all shadow-sm ${
            theme === "dark" ? "bg-zinc-950 border-zinc-900 hover:border-zinc-800" : "bg-white border-zinc-200 hover:border-zinc-300"
          }`}>
            <div className="flex justify-between items-center text-xs">
              <span className={`font-medium ${theme === "dark" ? "text-zinc-300" : "text-zinc-700"}`}>Vektör Ağırlığı (Alpha)</span>
              <span className={`px-2 py-0.5 rounded-md border font-mono text-xs font-semibold ${
                theme === "dark" ? "bg-rose-950/80 border-rose-800/50 text-rose-300" : "bg-rose-50 border-rose-200 text-rose-700"
              }`}>
                {alpha.toFixed(2)}
              </span>
            </div>
            <input
              type="range"
              min={0.0}
              max={1.0}
              step={0.05}
              value={alpha}
              onChange={(e) => setAlpha(Number(e.target.value))}
              className="w-full h-1.5 bg-zinc-700 accent-rose-600 rounded-lg appearance-none cursor-pointer"
            />
          </div>
        </div>
      </section>

      <hr className={theme === "dark" ? "border-zinc-900" : "border-zinc-200"} />

      {/* Belge Önizleme */}
      <section className="flex flex-col gap-3">
        <h2 className={`font-semibold flex items-center gap-2 ${theme === "dark" ? "text-zinc-200" : "text-zinc-900"}`}>
          <FileText className="w-4 h-4 text-rose-500" />
          Belge Önizleme
        </h2>

        {documents.length > 0 ? (
          <>
            <div className="relative" ref={selectRef}>
              <button
                type="button"
                onClick={() => setIsSelectOpen(!isSelectOpen)}
                className={`w-full flex items-center justify-between gap-2 border rounded-xl px-3 py-2.5 text-xs transition-all shadow-sm focus:outline-none ${
                  theme === "dark"
                    ? "bg-zinc-950/80 border-zinc-800 hover:border-zinc-700 focus:border-rose-500/50 text-zinc-200"
                    : "bg-white border-zinc-300 hover:border-zinc-400 focus:border-rose-500/50 text-zinc-800"
                }`}
              >
                <div className="flex items-center gap-2 truncate">
                  {selectedDoc && getFileIcon(selectedDoc)}
                  <span className={`truncate font-mono text-[11px] ${theme === "dark" ? "text-zinc-300" : "text-zinc-700"}`}>
                    {selectedDoc || "Belge seçiniz..."}
                  </span>
                </div>
                <ChevronDown className={`w-3.5 h-3.5 text-zinc-400 shrink-0 transition-transform duration-200 ${isSelectOpen ? "rotate-180 text-rose-500" : ""}`} />
              </button>

              {isSelectOpen && (
                <div className={`absolute left-0 right-0 top-full mt-1.5 z-50 max-h-56 overflow-y-auto backdrop-blur-md border rounded-xl shadow-2xl py-1 divide-y text-xs ${
                  theme === "dark"
                    ? "bg-zinc-950/95 border-zinc-800/80 divide-zinc-900/50 text-zinc-200"
                    : "bg-white/95 border-zinc-200 divide-zinc-100 text-zinc-800"
                }`}>
                  {documents.map((doc) => {
                    const isSelected = doc === selectedDoc;
                    return (
                      <button
                        key={doc}
                        type="button"
                        onClick={() => {
                          setSelectedDoc(doc);
                          setIsSelectOpen(false);
                        }}
                        className={`w-full text-left px-3 py-2 flex items-center justify-between gap-2 transition-colors ${
                          isSelected
                            ? theme === "dark"
                              ? "bg-rose-950/30 text-rose-300 font-medium border-l-2 border-rose-500"
                              : "bg-rose-50 text-rose-700 font-medium border-l-2 border-rose-500"
                            : theme === "dark"
                            ? "text-zinc-300 hover:bg-zinc-900/80 hover:text-zinc-100"
                            : "text-zinc-700 hover:bg-zinc-100 hover:text-zinc-900"
                        }`}
                      >
                        <div className="flex items-center gap-2 truncate">
                          {getFileIcon(doc)}
                          <span className="truncate font-mono text-[11px]">{doc}</span>
                        </div>
                        {isSelected && <div className="w-1.5 h-1.5 rounded-full bg-rose-500 shrink-0" />}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            <button
              onClick={handlePreview}
              disabled={isGenerating || !selectedDoc}
              className={`py-1.5 px-3 rounded-lg border disabled:opacity-40 transition-all flex items-center justify-center gap-2 text-xs ${
                theme === "dark"
                  ? "border-zinc-800 hover:border-zinc-700 bg-zinc-900/80 text-zinc-200"
                  : "border-zinc-300 hover:border-zinc-400 bg-white text-zinc-700"
              }`}
              title={isGenerating ? "⚠️ Yanıt üretimi devam ederken kullanılamaz." : "Seçilen belgenin metnini görüntüle."}
            >
              <Eye className="w-3.5 h-3.5" />
              Belgeyi Gör
            </button>
          </>
        ) : (
          <p className="text-xs text-zinc-500">Henüz indekslenmiş belge yok.</p>
        )}

        {previewContent !== null && (
          <div className="flex flex-col gap-2 mt-2">
            <div className={`flex items-center justify-between text-xs font-mono truncate ${
              theme === "dark" ? "text-zinc-400" : "text-zinc-600"
            }`}>
              <span>{selectedDoc}</span>
              <button
                onClick={() => setPreviewContent(null)}
                className={theme === "dark" ? "text-zinc-400 hover:text-zinc-200" : "text-zinc-600 hover:text-zinc-900"}
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
            <textarea
              readOnly
              value={previewContent}
              className={`w-full h-48 border rounded-lg p-2 text-xs font-mono resize-none focus:outline-none ${
                theme === "dark"
                  ? "bg-zinc-950 border-zinc-800 text-zinc-300"
                  : "bg-white border-zinc-300 text-zinc-800"
              }`}
            />
          </div>
        )}
      </section>

      {/* Sohbet Raporu İndir */}
      {messages.length > 0 && (
        <>
          <hr className={theme === "dark" ? "border-zinc-900" : "border-zinc-200"} />
          <button
            onClick={handleDownloadReport}
            className={`w-full py-2 px-3 rounded-lg border transition-all flex items-center justify-center gap-2 text-xs ${
              theme === "dark"
                ? "border-zinc-800 bg-zinc-900 hover:bg-zinc-800 text-zinc-200"
                : "border-zinc-300 bg-white hover:bg-zinc-50 text-zinc-700"
            }`}
          >
            <Download className="w-3.5 h-3.5" />
            Sohbet Raporunu İndir (.md)
          </button>
        </>
      )}
    </aside>
  );
};
