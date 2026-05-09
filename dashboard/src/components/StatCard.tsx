interface Props {
  label: string
  value: string
  icon: string
}

const card: React.CSSProperties = {
  background: '#1a1d27',
  borderRadius: 12,
  padding: '24px 28px',
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
}

export default function StatCard({ label, value, icon }: Props) {
  return (
    <div style={card}>
      <span style={{ fontSize: 28 }}>{icon}</span>
      <span style={{ fontSize: 32, fontWeight: 700, color: '#7c6af7' }}>{value}</span>
      <span style={{ color: '#94a3b8', fontSize: 14 }}>{label}</span>
    </div>
  )
}
