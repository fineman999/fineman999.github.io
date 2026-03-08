export function FilterBar({ sites, selectedId, onSelect }) {
  return (
    <div className="flex gap-2 overflow-x-auto pb-1">
      <button
        onClick={() => onSelect(null)}
        className={`shrink-0 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
          selectedId === null
            ? 'bg-slate-800 text-white'
            : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
        }`}
      >
        전체
      </button>
      {sites.map(site => (
        <button
          key={site.id}
          onClick={() => onSelect(site.id)}
          className={`shrink-0 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
            selectedId === site.id
              ? 'bg-slate-800 text-white'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          {site.name}
        </button>
      ))}
    </div>
  )
}
