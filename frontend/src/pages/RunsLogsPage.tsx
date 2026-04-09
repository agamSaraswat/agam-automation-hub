import { ActivityItem } from "../types/api";

type RunsLogsPageProps = {
  activity: ActivityItem[];
};

export function RunsLogsPage({ activity }: RunsLogsPageProps) {
  return (
    <section className="panel">
      <h2>Runs & Logs</h2>
      {activity.length === 0 ? (
        <p>No recent activity yet.</p>
      ) : (
        <ul className="activity-list">
          {activity.map((item) => (
            <li key={item.id}>
              <strong>{item.action}</strong>
              <span>{item.result}</span>
              <small>{item.timestamp}</small>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
