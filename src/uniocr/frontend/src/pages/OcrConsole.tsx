import { useState, useRef, useEffect } from 'react';
import { UploadCloud, FileType, Type, FileJson, Loader2, Download, ScanText } from 'lucide-react';


export default function OcrConsole({ isPublic }: { isPublic: boolean }) {
  const [file, setFile] = useState<File | null>(null);
  const [engine, setEngine] = useState(() => localStorage.getItem('preferredEngine') || 'auto');
  const [format, setFormat] = useState('markdown');
  const [loading, setLoading] = useState(false);
  
  const [result, setResult] = useState<any>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);

  // Remember engine preference
  useEffect(() => {
    localStorage.setItem('preferredEngine', engine);
  }, [engine]);

  // Auto scroll logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const handleProcess = async () => {
    if (!file) return;
    setLoading(true);
    setResult(null);
    setPdfUrl(null);
    setLogs(["[SYSTEM] Starting extraction process..."]);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('engine', engine);
    formData.append('format', format);

    try {
      const token = localStorage.getItem('token');
      const headers: Record<string, string> = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;

      if (format === 'pdf') {
        // SSE for PDF is harder because it's binary. The /stream endpoint returns JSON.
        // Wait, the /stream endpoint returns JSON for all formats currently, but for PDF we need a binary file.
        // The original /extract/pdf was used for PDF.
        // Let's keep using the standard endpoint for PDF but maybe we can't stream logs easily for it unless we use SSE then download.
        // For simplicity, if PDF, we just do normal POST, no logs, or we can use the old endpoint.
        setLogs(prev => [...prev, "[SYSTEM] PDF extraction uses standard blocking call currently."]);
        const res = await fetch('/extract/pdf', {
          method: 'POST',
          headers,
          body: formData
        });
        if (!res.ok) throw new Error('PDF Extraction failed');
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        setPdfUrl(url);
        setLogs(prev => [...prev, "[SYSTEM] PDF Generation complete!"]);
        setLoading(false);
        return;
      }

      // SSE flow for text/json/markdown
      const response = await fetch('/extract/stream', {
        method: 'POST',
        headers,
        body: formData
      });

      if (!response.ok) {
        throw new Error('Stream request failed');
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const dataStr = line.replace('data: ', '');
              try {
                const data = JSON.parse(dataStr);
                if (data.type === 'log') {
                  setLogs(prev => [...prev, `[ENGINE] ${data.message}`]);
                } else if (data.type === 'result') {
                  setResult(data.data);
                  setLogs(prev => [...prev, "[SYSTEM] Extraction complete!"]);
                } else if (data.type === 'error') {
                  setLogs(prev => [...prev, `[ERROR] ${data.message}`]);
                }
              } catch (e) {}
            }
          }
        }
      }
    } catch (err: any) {
      console.error(err);
      setLogs(prev => [...prev, `[SYSTEM ERROR] ${err.message}`]);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = (content: string, filename: string, mimeType: string) => {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const renderDownloadButton = () => {
    if (format === 'pdf' && pdfUrl) {
      return (
        <a href={pdfUrl} download={`searchable_${file?.name || 'document'}.pdf`} className="glass-button bg-white/10 hover:bg-white/20 text-white flex items-center gap-2 text-sm border border-white/20 backdrop-blur-md px-3 py-1.5 rounded-lg transition-colors">
          <Download size={14} /> Download PDF
        </a>
      );
    }

    if (result && format !== 'pdf') {
      let displayContent = '';
      let dlExt = 'txt';
      let dlMime = 'text/plain';

      if (format === 'markdown') {
        displayContent = result.markdown;
        dlExt = 'md';
        dlMime = 'text/markdown';
      } else if (format === 'text') {
        displayContent = result.text;
      } else if (format === 'json') {
        displayContent = JSON.stringify(result, null, 2);
        dlExt = 'json';
        dlMime = 'application/json';
      }

      return (
        <button 
          onClick={() => handleDownload(displayContent, `extraction.${dlExt}`, dlMime)}
          className="glass-button bg-white/10 hover:bg-white/20 text-white flex items-center gap-2 text-sm border border-white/20 backdrop-blur-md px-3 py-1.5 rounded-lg transition-colors"
        >
          <Download size={14} /> Download .{dlExt}
        </button>
      );
    }
    return null;
  };

  const renderResult = () => {
    if (format === 'pdf' && pdfUrl) {
      return (
        <div className="absolute inset-0">
          <iframe src={pdfUrl} className="w-full h-full border-0" title="PDF Preview" />
        </div>
      );
    }

    if (!result || (format === 'pdf' && !pdfUrl)) return (
      <div className="h-full flex items-center justify-center text-white/30">
        Results will appear here
      </div>
    );

    let displayContent = '';
    if (format === 'markdown') displayContent = result.markdown;
    else if (format === 'text') displayContent = result.text;
    else if (format === 'json') displayContent = JSON.stringify(result, null, 2);

    return (
      <div className="flex flex-col h-full">
        <pre className="p-6 h-full overflow-auto text-sm text-white/80 whitespace-pre-wrap font-mono custom-scrollbar">
          {displayContent}
        </pre>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full gap-6 p-6">
      <header className="flex justify-between items-center">
        <div>
          <h2 className="text-3xl font-bold text-white tracking-tight">Console</h2>
          <p className="text-white/50">Extract text and structures from documents</p>
        </div>
        {!isPublic && (
          <span className="px-3 py-1 rounded-full bg-red-500/20 border border-red-500/30 text-red-400 text-xs font-bold tracking-wider">
            PRIVATE INSTANCE
          </span>
        )}
      </header>

      <div className="flex flex-col lg:flex-row gap-6 flex-1 min-h-0">
        
        {/* Left Column: Controls & Logs */}
        <div className="w-full lg:w-96 flex flex-col gap-6">
          
          <div className="glass-panel p-8 flex flex-col gap-6">
            <div className="flex flex-col gap-3">
              <div className="text-xs font-semibold text-white/40 tracking-wider">SOURCE</div>
              <div 
                className="border border-white/5 hover:border-white/20 bg-black/20 rounded-xl p-8 flex flex-col items-center justify-center gap-4 cursor-pointer transition-all"
              onClick={() => fileInputRef.current?.click()}
            >
              <UploadCloud size={32} className="text-white/50" />
              <div className="text-center">
                <p className="font-medium text-white">{file ? file.name : "Select or drop file"}</p>
                <p className="text-xs text-white/40 mt-1">Image or PDF format</p>
              </div>
              <input type="file" className="hidden" ref={fileInputRef} onChange={e => setFile(e.target.files?.[0] || null)} />
            </div>

            </div>

            <div className="flex flex-col gap-3 mt-2">
              <div className="text-xs font-semibold text-white/40 tracking-wider">ENGINE</div>
            <select value={engine} onChange={e => setEngine(e.target.value)} className="glass-input w-full appearance-none">
              <option value="auto" className="bg-gray-900">Auto (Best Match)</option>
              <option value="paddle" className="bg-gray-900">PaddleOCR-VL (Deep Doc)</option>
              <option value="apple" className="bg-gray-900">Apple Vision (Native)</option>
            </select>

            </div>

            <div className="flex flex-col gap-3 mt-2">
              <div className="text-xs font-semibold text-white/40 tracking-wider">FORMAT</div>
            <div className="grid grid-cols-2 gap-2">
              {[
                { id: 'markdown', icon: Type, label: 'Markdown' },
                { id: 'text', icon: Type, label: 'Raw Text' },
                { id: 'json', icon: FileJson, label: 'JSON' },
                { id: 'pdf', icon: FileType, label: 'Searchable PDF' },
              ].map(fmt => (
                <button
                  key={fmt.id}
                  onClick={() => setFormat(fmt.id)}
                  className={`flex flex-col items-center gap-2 p-3 rounded-xl border transition-all ${format === fmt.id ? 'bg-primary/20 border-primary text-white' : 'bg-white/5 border-white/10 text-white/60 hover:bg-white/10'}`}
                >
                  <fmt.icon size={20} />
                  <span className="text-xs font-medium">{fmt.label}</span>
                </button>
              ))}
            </div>
            </div>

            <button 
              onClick={handleProcess} 
              disabled={!file || loading}
              className={`glass-button-primary w-full mt-6 flex items-center justify-center gap-2 py-3 ${(!file || loading) && 'opacity-50 pointer-events-none'}`}
            >
              {loading ? <Loader2 className="animate-spin" size={20} /> : <ScanText size={20} />}
              {loading ? 'Processing...' : 'Run Extraction'}
            </button>
          </div>

          {/* Terminal Log Panel */}
          <div className="glass-panel flex-1 min-h-[200px] flex flex-col overflow-hidden bg-[#050505]">
            <div className="flex-1 overflow-auto p-5 custom-scrollbar font-mono text-[11px] leading-relaxed text-white/60">
              {logs.length === 0 ? (
                <span className="text-white/20">Waiting for extraction to start...</span>
              ) : (
                logs.map((log, i) => (
                  <div key={i} className={`${log.includes('[ERROR]') ? 'text-red-400' : log.includes('[SYSTEM]') ? 'text-primary/80' : 'text-green-400/80'} mb-1 break-all`}>
                    {log}
                  </div>
                ))
              )}
              <div ref={logsEndRef} />
            </div>
          </div>

        </div>

        {/* Results Panel */}
        <div className="flex-1 glass-panel flex flex-col overflow-hidden min-h-[400px]">
          <div className="border-b border-white/5 p-4 bg-transparent flex justify-between items-center min-h-[60px]">
            <div className="text-xs font-semibold text-white/40 tracking-wider">OUTPUT</div>
            {renderDownloadButton()}
          </div>
          <div className="flex-1 overflow-hidden relative">
            {renderResult()}
          </div>
        </div>
      </div>
    </div>
  );
}
