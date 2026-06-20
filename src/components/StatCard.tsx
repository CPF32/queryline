export interface StatCardProps {
  title: string;
  value: string | number;
}

export default function StatCard({ title, value }: StatCardProps) {
  return (
    <div className="stat-card">
      <div className="stat-card__label">{title}</div>
      <div className="stat-card__value">{value}</div>
    </div>
  );
}
