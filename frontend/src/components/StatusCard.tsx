type StatusCardProps = {
  title: string;
  value: string;
  detail?: string;
};

export function StatusCard({ title, value, detail }: StatusCardProps) {
  return (
    <article className="status-card">
      <p className="status-card-title">{title}</p>
      <p className="status-card-value">{value}</p>
      {detail && <p className="status-card-detail">{detail}</p>}
    </article>
  );
}
