export default function ApiDocs() {
  return (
    <div className="flex flex-col h-full gap-6 p-6">
      <header>
        <h2 className="text-3xl font-bold text-white tracking-tight">API Reference</h2>
        <p className="text-white/50">Integrate UniOCR into your workflows and applications</p>
      </header>

      <div className="flex-1 glass-panel overflow-hidden">
        <iframe 
          src="/docs" 
          className="w-full h-full bg-white border-0"
          title="Swagger UI"
        />
      </div>
    </div>
  );
}
