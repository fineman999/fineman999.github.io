import { formatDistanceToNow } from 'date-fns'
import { ko } from 'date-fns/locale'

export function FeedCard({ item }) {
  const timeAgo = formatDistanceToNow(
    new Date(item.scraped_at),
    { addSuffix: true, locale: ko }
  )

  return (
    <a
      href={item.link}
      target="_blank"
      rel="noopener noreferrer"
      className="block rounded-xl border border-slate-200 bg-white p-4 shadow-sm hover:shadow-md transition-shadow"
    >
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
          {item.sites?.name ?? ''}
        </span>
        <span className="text-xs text-slate-400">{timeAgo}</span>
      </div>
      <p className="text-sm font-semibold text-slate-800 line-clamp-2">{item.title}</p>
      {item.summary && (
        <p className="mt-1 text-xs text-slate-500 line-clamp-2">{item.summary}</p>
      )}
    </a>
  )
}
