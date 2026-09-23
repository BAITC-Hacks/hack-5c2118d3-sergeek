import type { LucideIcon } from 'lucide-react'

export function MetricCard({ label, value, note, icon: Icon, emphasis }: { label: string; value: string; note: string; icon: LucideIcon; emphasis?: boolean }) {
  return <article className={`metric-card ${emphasis ? 'emphasis' : ''}`}><span className="metric-icon"><Icon size={18} /></span><div><p>{label}</p><strong>{value}</strong><small>{note}</small></div></article>
}
