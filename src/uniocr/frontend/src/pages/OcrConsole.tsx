import { useState, useRef } from 'react';
import axios from 'axios';
import { UploadCloud, FileType, Type, FileJson, Loader2, Download, ScanText } from 'lucide-react';

export default function OcrConsole({ isPublic }: { isPublic: boolean }) {
  const [file, setFile] = useState<File | null>(null);
  const [engine, setEngine] = useState('auto');
  const [format, setFormat] = useState('markdown');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleProcess = async () => {
    if (!file) return;
    setLoading(true);
    setResult(null);
    setPdfUrl(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('engine', engine);

    try {
      if (format === 'pdf') {
        const res = await axios.post('/extract/pdf', formData, {
          responseType: 'blob'
        });
        const url = window.URL.createObjectURL(new Blob([res.data]));
        setPdfUrl(url);
      } else {
        const res = await axios.post('/extract', formData);
        setResult(res.data);
      }
    } catch (err) {
      console.error(err);
      alert('Extraction failed');
    } finally {
      setLoading(false);
    }
  };

  const renderResult = () => {
    if (pdfUrl) {
      return (
        <div className="h-full flex flex-col items-center justify-center text-center p-8 gap-4">
          <div className="w-16 h-16 rounded-full bg-green-500/20 flex items-center justify-center">
            <Download className="text-green-400" size={32} />
          </div>
          <h3 className="text-xl font-bold">Searchable PDF Generated!</h3>
          <p className="text-white/50 mb-4">Your document has been overlayed with invisible searchable text.</p>
          <a href={pdfUrl} download={`searchable_${file?.name}.pdf`} className="glass-button-primary">
            Download PDF
          </a>
        </div>
      );
    }

    if (!result) return (
      <div className="h-full flex items-center justify-center text-white/30">
        Results will appear here
      </div>
    );

    let displayContent = '';
    if (format === 'markdown') displayContent = result.markdown;
    if (format === 'text') displayContent = result.text;
    if (format === 'json') displayContent = JSON.stringify(result, null, 2);

    return (
      <pre className="p-6 h-full overflow-auto text-sm text-white/80 whitespace-pre-wrap font-mono custom-scrollbar">
        {displayContent}
      </pre>
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
        {/* Controls Panel */}
        <div className="w-full lg:w-80 flex flex-col gap-6">
          <div className="glass-panel p-6 flex flex-col gap-4">
            <h3 className="font-semibold text-white/80 mb-2">1. Upload Source</h3>
            <div 
              className="border-2 border-dashed border-white/20 hover:border-primary/50 bg-white/5 rounded-xl p-8 flex flex-col items-center justify-center gap-4 cursor-pointer transition-all"
              onClick={() => fileInputRef.current?.click()}
            >
              <UploadCloud size={32} className="text-white/50" />
              <div className="text-center">
                <p className="font-medium">{file ? file.name : "Select or drop file"}</p>
                <p className="text-xs text-white/40 mt-1">Image or PDF format</p>
              </div>
              <input type="file" className="hidden" ref={fileInputRef} onChange={e => setFile(e.target.files?.[0] || null)} />
            </div>

            <h3 className="font-semibold text-white/80 mt-4 mb-2">2. Processing Engine</h3>
            <select value={engine} onChange={e => setEngine(e.target.value)} className="glass-input w-full appearance-none">
              <option value="auto" className="bg-gray-900">Auto (Best Match)</option>
              <option value="paddle" className="bg-gray-900">PaddleOCR-VL (Deep Doc)</option>
              <option value="apple" className="bg-gray-900">Apple Vision (Native)</option>
            </select>

            <h3 className="font-semibold text-white/80 mt-4 mb-2">3. Output Format</h3>
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

            <button 
              onClick={handleProcess} 
              disabled={!file || loading}
              className={`glass-button-primary w-full mt-6 flex items-center justify-center gap-2 py-3 ${(!file || loading) && 'opacity-50 pointer-events-none'}`}
            >
              {loading ? <Loader2 className="animate-spin" size={20} /> : <ScanText size={20} />}
              {loading ? 'Processing...' : 'Run Extraction'}
            </button>
          </div>
        </div>

        {/* Results Panel */}
        <div className="flex-1 glass-panel flex flex-col overflow-hidden min-h-[400px]">
          <div className="border-b border-white/10 p-4 bg-white/5 flex justify-between items-center">
            <h3 className="font-semibold text-white/80">Result Output</h3>
            {result && <span className="text-xs text-white/40">Took {result.elapsed_seconds?.toFixed(2)}s</span>}
          </div>
          <div className="flex-1 overflow-hidden relative">
            {renderResult()}
          </div>
        </div>
      </div>
    </div>
  );
}
