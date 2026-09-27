// Marca da MarIA, do protótipo (logo_maria).
export default function Logo({ className = "" }) {
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <svg width="44" height="44" viewBox="0 0 48 48" fill="none" aria-hidden="true">
        <rect width="48" height="48" rx="14" fill="#4A7C59" fillOpacity="0.12" />
        <path
          d="M14 34C14 24.0589 22.0589 16 32 16C37.5228 16 42 20.4772 42 26C42 31.5228 37.5228 36 32 36C28.6863 36 26 33.3137 26 30"
          stroke="#3D664A"
          strokeWidth="3"
          strokeLinecap="round"
        />
        <circle cx="20" cy="20" r="3" fill="#4A7C59" />
        <circle cx="34" cy="24" r="2.5" fill="#4A7C59" />
      </svg>
      <div className="leading-tight">
        <div className="text-xl font-bold tracking-tight text-slate">
          Mar<span className="text-primary">IA</span>
        </div>
        <div className="text-[10.5px] font-medium tracking-wider text-muted">ASSISTENTE CLÍNICA</div>
      </div>
    </div>
  );
}
