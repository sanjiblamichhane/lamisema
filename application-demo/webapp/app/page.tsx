'use client';

import { useState, useCallback, useRef, DragEvent, ChangeEvent } from 'react';

// ─── Types ────────────────────────────────────────────────────────────────────

type Phase = 'idle' | 'uploading' | 'uploaded' | 'preflighting' | 'preflighted' | 'extracting' | 'done';

interface UploadResult {
  doc_id: string;
  filename: string;
  size_bytes: number;
}

interface FontInfo {
  name: string;
  encoding: string | null;
  is_legacy_nepali: boolean;
}

interface PreflightResult {
  doc_id: string;
  filename: string;
  page_count: number;
  encoding_type: 'unicode_native' | 'legacy_encoded' | 'scanned' | 'unknown';
  fonts: FontInfo[];
  has_text_layer: boolean;
  recommended_strategy: string;
}

interface Entity {
  text: string;
  entity_type: string;
  normalized?: string;
  confidence: number;
}

interface PageResult {
  page_number: number;
  raw_text: string;
  script_ratio: number;
  entities: Entity[];
  extraction_method: string;
  confidence: number;
}

interface ExtractionResult {
  doc_id: string;
  filename: string;
  language: string;
  encoding_type: string;
  total_pages: number;
  pages: PageResult[];
  overall_confidence: number;
  ocr_backend: string;
  warnings: string[];
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const ENCODING_LABELS: Record<string, { label: string; cls: string }> = {
  unicode_native: { label: 'Unicode Native', cls: 'bg-green-100 text-green-800' },
  legacy_encoded: { label: 'Legacy Encoded (Preeti/Kantipur)', cls: 'bg-orange-100 text-orange-800' },
  scanned: { label: 'Scanned PDF', cls: 'bg-blue-100 text-blue-800' },
  unknown: { label: 'Unknown', cls: 'bg-gray-100 text-gray-700' },
};

const ENTITY_COLORS: Record<string, string> = {
  DATE_BS: 'bg-purple-100 text-purple-800',
  DATE_AD: 'bg-indigo-100 text-indigo-800',
  CURRENCY: 'bg-yellow-100 text-yellow-800',
  ORGANIZATION: 'bg-blue-100 text-blue-800',
  PERSON: 'bg-pink-100 text-pink-800',
  LOCATION: 'bg-teal-100 text-teal-800',
  DISTRICT: 'bg-cyan-100 text-cyan-800',
  PHONE: 'bg-green-100 text-green-800',
  EMAIL: 'bg-orange-100 text-orange-800',
};

function formatBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function groupEntities(entities: Entity[]): Record<string, Entity[]> {
  return entities.reduce((acc, e) => {
    (acc[e.entity_type] ??= []).push(e);
    return acc;
  }, {} as Record<string, Entity[]>);
}

function EncodingBadge({ type }: { type: string }) {
  const { label, cls } = ENCODING_LABELS[type] ?? ENCODING_LABELS.unknown;
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${cls}`}>
      {label}
    </span>
  );
}

function Spinner() {
  return (
    <svg className="animate-spin h-4 w-4 text-white inline mr-2" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
    </svg>
  );
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function ExtractionPanel({ result }: { result: ExtractionResult }) {
  const [expandedPage, setExpandedPage] = useState<number | null>(null);
  const allEntities = result.pages.flatMap(p => p.entities);
  const grouped = groupEntities(allEntities);

  return (
    <div className="space-y-5">
      {/* Summary cards */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-gray-900">Extraction Results</h2>
          <EncodingBadge type={result.encoding_type} />
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: 'Pages', value: result.total_pages },
            { label: 'Confidence', value: `${(result.overall_confidence * 100).toFixed(0)}%` },
            { label: 'Entities', value: allEntities.length },
            { label: 'OCR Backend', value: result.ocr_backend },
          ].map(({ label, value }) => (
            <div key={label} className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-500">{label}</p>
              <p className="text-lg font-bold text-gray-900 mt-0.5 truncate">{value}</p>
            </div>
          ))}
        </div>
        {result.warnings.length > 0 && (
          <div className="mt-4 bg-yellow-50 border border-yellow-200 rounded-lg p-3">
            <p className="text-xs font-semibold text-yellow-800 mb-1">Warnings</p>
            {result.warnings.map((w, i) => (
              <p key={i} className="text-xs text-yellow-700">{w}</p>
            ))}
          </div>
        )}
      </div>

      {/* Entities grouped by type */}
      {Object.keys(grouped).length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Extracted Entities</h3>
          <div className="space-y-5">
            {Object.entries(grouped).map(([type, entities]) => (
              <div key={type}>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                  {type} <span className="font-normal normal-case">({entities.length})</span>
                </p>
                <div className="flex flex-wrap gap-2">
                  {entities.map((e, i) => (
                    <span
                      key={i}
                      title={e.normalized ?? e.text}
                      className={`inline-flex flex-col px-2.5 py-1.5 rounded text-xs leading-tight ${ENTITY_COLORS[type] ?? 'bg-gray-100 text-gray-700'}`}
                    >
                      <span className="font-medium">{e.text}</span>
                      {e.normalized && <span className="opacity-60 text-[10px] mt-0.5">{e.normalized}</span>}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Page breakdown */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="font-semibold text-gray-900 mb-4">Pages</h3>
        <div className="space-y-2">
          {result.pages.map(page => (
            <div key={page.page_number} className="border border-gray-200 rounded-lg overflow-hidden">
              <button
                onClick={() => setExpandedPage(expandedPage === page.page_number ? null : page.page_number)}
                className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 transition-colors text-left"
              >
                <div className="flex items-center gap-2.5 flex-wrap">
                  <span className="text-sm font-medium text-gray-900">Page {page.page_number}</span>
                  <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded font-mono">
                    {page.extraction_method}
                  </span>
                  {page.entities.length > 0 && (
                    <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                      {page.entities.length} entities
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-xs text-gray-400">
                    {(page.confidence * 100).toFixed(0)}% confidence
                  </span>
                  <span className="text-gray-400">{expandedPage === page.page_number ? '▲' : '▼'}</span>
                </div>
              </button>
              {expandedPage === page.page_number && (
                <div className="px-4 pb-4 border-t border-gray-100">
                  {page.raw_text ? (
                    <pre className="mt-3 bg-gray-50 rounded-lg p-3 text-xs text-gray-700 whitespace-pre-wrap font-mono max-h-52 overflow-y-auto leading-relaxed">
                      {page.raw_text}
                    </pre>
                  ) : (
                    <p className="mt-3 text-xs text-gray-400 italic">No text extracted from this page.</p>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function Home() {
  const [phase, setPhase] = useState<Phase>('idle');
  const [dragOver, setDragOver] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [upload, setUpload] = useState<UploadResult | null>(null);
  const [preflight, setPreflight] = useState<PreflightResult | null>(null);
  const [extraction, setExtraction] = useState<ExtractionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const loading = ['uploading', 'preflighting', 'extracting'].includes(phase);

  const reset = () => {
    setPhase('idle');
    setFile(null);
    setUpload(null);
    setPreflight(null);
    setExtraction(null);
    setError(null);
  };

  const handleDrop = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f?.name.toLowerCase().endsWith('.pdf')) setFile(f);
  }, []);

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) setFile(f);
  };

  const handleUpload = async () => {
    if (!file) return;
    setPhase('uploading');
    setError(null);
    try {
      const form = new FormData();
      form.append('file', file);
      const res = await fetch('/api/upload', { method: 'POST', body: form });
      if (!res.ok) throw new Error((await res.json()).detail ?? res.statusText);
      setUpload(await res.json());
      setPhase('uploaded');
    } catch (e) {
      setError(String(e));
      setPhase('idle');
    }
  };

  const handlePreflight = async () => {
    if (!upload) return;
    setPhase('preflighting');
    setError(null);
    try {
      const res = await fetch(`/api/preflight/${upload.doc_id}`);
      if (!res.ok) throw new Error((await res.json()).detail ?? res.statusText);
      setPreflight(await res.json());
      setPhase('preflighted');
    } catch (e) {
      setError(String(e));
      setPhase('uploaded');
    }
  };

  const handleExtract = async () => {
    if (!upload) return;
    setPhase('extracting');
    setError(null);
    try {
      const res = await fetch(`/api/extract/${upload.doc_id}`, { method: 'POST' });
      if (!res.ok) throw new Error((await res.json()).detail ?? res.statusText);
      setExtraction(await res.json());
      setPhase('done');
    } catch (e) {
      setError(String(e));
      setPhase('preflighted');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-5 py-4 flex items-center justify-between">
          <div>
            <span className="text-lg font-bold text-gray-900">LamiSema</span>
            <span className="ml-2 text-xs text-gray-400 hidden sm:inline">
              Structured extraction for Nepali PDFs
            </span>
          </div>
          {upload && (
            <button onClick={reset} className="text-sm text-gray-500 hover:text-gray-800 underline underline-offset-2">
              New document
            </button>
          )}
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-5 py-8 space-y-5">
        {/* Error banner */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700 flex justify-between items-start">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="ml-4 text-red-400 hover:text-red-600 font-bold">✕</button>
          </div>
        )}

        {/* Step 1: Upload */}
        {!upload && (
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="font-semibold text-gray-900 mb-1">Upload a Nepali PDF</h2>
            <p className="text-xs text-gray-500 mb-4">
              Supports Unicode, Preeti/Kantipur legacy fonts, and scanned documents.
            </p>
            <div
              onDrop={handleDrop}
              onDragOver={e => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onClick={() => fileRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors select-none ${
                dragOver
                  ? 'border-blue-400 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-400 hover:bg-gray-50'
              }`}
            >
              <input ref={fileRef} type="file" accept=".pdf" className="hidden" onChange={handleFileChange} />
              {file ? (
                <div>
                  <p className="text-sm font-medium text-gray-900">{file.name}</p>
                  <p className="text-xs text-gray-400 mt-1">{formatBytes(file.size)}</p>
                </div>
              ) : (
                <div>
                  <p className="text-2xl mb-2">📄</p>
                  <p className="text-sm text-gray-600">Drag & drop a PDF, or click to browse</p>
                </div>
              )}
            </div>
            {file && (
              <button
                onClick={handleUpload}
                disabled={loading}
                className="mt-4 w-full py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white rounded-lg text-sm font-medium transition-colors"
              >
                {phase === 'uploading' ? <><Spinner />Uploading…</> : 'Upload PDF'}
              </button>
            )}
          </div>
        )}

        {/* Step 2: Uploaded — doc info + preflight trigger */}
        {upload && phase !== 'done' && (
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <p className="font-medium text-gray-900 truncate">{upload.filename}</p>
                <p className="text-xs text-gray-500 mt-0.5">
                  <code className="bg-gray-100 px-1.5 py-0.5 rounded font-mono">{upload.doc_id}</code>
                  <span className="ml-2">{formatBytes(upload.size_bytes)}</span>
                </p>
              </div>
              <span className="shrink-0 text-xs bg-green-100 text-green-700 px-2.5 py-1 rounded-full font-medium">
                Uploaded
              </span>
            </div>

            {!preflight && (
              <button
                onClick={handlePreflight}
                disabled={loading}
                className="mt-4 py-2.5 px-4 bg-gray-800 hover:bg-gray-900 disabled:opacity-60 text-white rounded-lg text-sm font-medium transition-colors"
              >
                {phase === 'preflighting' ? <><Spinner />Analysing encoding…</> : 'Run Pre-flight Analysis'}
              </button>
            )}
          </div>
        )}

        {/* Step 3: Preflight results */}
        {preflight && (
          <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-gray-900">Pre-flight Analysis</h2>
              <EncodingBadge type={preflight.encoding_type} />
            </div>

            <div className="grid grid-cols-3 gap-3">
              {[
                { label: 'Pages', value: preflight.page_count },
                { label: 'Text Layer', value: preflight.has_text_layer ? 'Yes' : 'No' },
                { label: 'Fonts', value: preflight.fonts.length },
              ].map(({ label, value }) => (
                <div key={label} className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-500">{label}</p>
                  <p className="text-xl font-bold text-gray-900 mt-0.5">{value}</p>
                </div>
              ))}
            </div>

            {preflight.fonts.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Detected Fonts</p>
                <div className="flex flex-wrap gap-1.5">
                  {preflight.fonts.map(f => (
                    <span
                      key={f.name}
                      className={`text-xs px-2.5 py-1 rounded-full ${
                        f.is_legacy_nepali
                          ? 'bg-orange-100 text-orange-800'
                          : 'bg-gray-100 text-gray-700'
                      }`}
                    >
                      {f.name}{f.is_legacy_nepali ? ' ⚠' : ''}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div className="bg-blue-50 border border-blue-100 rounded-lg p-3">
              <p className="text-xs font-semibold text-blue-800 mb-1">Recommended Strategy</p>
              <p className="text-xs text-blue-700 leading-relaxed">{preflight.recommended_strategy}</p>
            </div>

            {phase !== 'done' && (
              <button
                onClick={handleExtract}
                disabled={loading}
                className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white rounded-lg text-sm font-medium transition-colors"
              >
                {phase === 'extracting'
                  ? <><Spinner />Extracting… (OCR PDFs may take up to 2 min)</>
                  : 'Run Full Extraction'}
              </button>
            )}
          </div>
        )}

        {/* Step 4: Extraction results */}
        {extraction && <ExtractionPanel result={extraction} />}
      </main>
    </div>
  );
}
