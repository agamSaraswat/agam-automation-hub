import { useEffect, useMemo, useState } from "react";

import { apiClient } from "../api/client";
import { StatusCard } from "../components/StatusCard";
import { ActivityItem, HealthResponse, SchedulerStatus, SystemStatus } from "../types/api";

type DashboardPageProps = {
  onAddActivity: (entry: Omit<ActivityItem, "id" | "timestamp">) => void;
  activity: ActivityItem[];
};

export function DashboardPage({ onAddActivity, activity }: DashboardPageProps) {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [schedulerStatus, setSchedulerStatus] = useState<SchedulerStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [runningAction, setRunningAction] = useState<string | null>(null);
  const [schedulerAction, setSchedulerAction] = useState<string | null>(null);

  const configuredServices = useMemo(() => {
    if (!status) return 0;
    return Object.values(status.environment).filter((item) => item.set).length;
  }, [status]);

  async function loadDashboardData() {
    setLoading(true);
    setError("");
    try {
      const [healthResponse, statusResponse, schedulerResponse] = await Promise.all([
        apiClient.getHealth(),
        apiClient.getStatus(),
        apiClient.getSchedulerStatus(),
      ]);
      setHealth(healthResponse);
      setStatus(statusResponse);
      setSchedulerStatus(schedulerResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load dashboard");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDashboardData();
  }, []);

  async function runQuickAction(action: "jobs" | "briefing" | "gmail") {
    setRunningAction(action);
    try {
      if (action === "jobs") {
        const result = await apiClient.runJobs();
        onAddActivity({
          action: "Run Jobs",
          result: `Scraped ${result.scraped_new_jobs}, tailored ${result.tailored_jobs}`,
        });
      }
      if (action === "briefing") {
        await apiClient.runBriefing(false);
        onAddActivity({ action: "Run Briefing", result: "Briefing generated" });
      }
      if (action === "gmail") {
        await apiClient.runGmail(false);
        onAddActivity({ action: "Run Gmail Triage", result: "Gmail triage completed" });
      }
      await loadDashboardData();
    } catch (err) {
      onAddActivity({
        action: `Run ${action}`,
        result: err instanceof Error ? err.message : "Action failed",
      });
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setRunningAction(null);
    }
  }

  async function runSchedulerAction(action: "start" | "stop") {
    const confirmed = window.confirm(
      action === "start"
        ? "Start scheduler background automations now?"
        : "Stop scheduler background automations now?",
    );
    if (!confirmed) {
      return;
    }

    setSchedulerAction(action);
    setError("");
    try {
      const result = action === "start"
        ? await apiClient.startScheduler(true)
        : await apiClient.stopScheduler(true);
      setSchedulerStatus(result);
      onAddActivity({
        action: action === "start" ? "Start Scheduler" : "Stop Scheduler",
        result: result.running ? "Scheduler is running" : "Scheduler is stopped",
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Scheduler action failed");
    } finally {
      setSchedulerAction(null);
    }
  }

  if (loading) {
    return <p className="panel">Loading dashboard...</p>;
  }

  if (error) {
    return <p className="panel error">{error}</p>;
  }

  if (!health || !status) {
    return <p className="panel error">Dashboard data unavailable.</p>;
  }

  return (
    <div className="page-stack">
      <section className="grid-cards">
        <StatusCard title="API Health" value={health.status.toUpperCase()} detail={health.service} />
        <StatusCard title="Service Date" value={health.date} detail="From backend health endpoint" />
        <StatusCard
          title="Configured Services"
          value={`${configuredServices}/${Object.keys(status.environment).length}`}
          detail="Environment variables currently set"
        />
        <StatusCard
          title="Today's Queue"
          value={String(status.jobs.today_queued)}
          detail={`Total tracked jobs: ${status.jobs.total_jobs}`}
        />
      </section>

      <section className="panel">
        <h2>Quick Actions</h2>
        <div className="button-row">
          <button onClick={() => runQuickAction("jobs")} disabled={runningAction !== null}>
            {runningAction === "jobs" ? "Running..." : "Run Jobs"}
          </button>
          <button onClick={() => runQuickAction("briefing")} disabled={runningAction !== null}>
            {runningAction === "briefing" ? "Running..." : "Run Briefing"}
          </button>
          <button onClick={() => runQuickAction("gmail")} disabled={runningAction !== null}>
            {runningAction === "gmail" ? "Running..." : "Run Gmail Triage"}
          </button>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>Scheduler Controls</h2>
          <span>{schedulerStatus?.running ? "Running" : "Stopped"}</span>
        </div>

        <div className="button-row">
          <button onClick={() => runSchedulerAction("start")} disabled={schedulerAction !== null || schedulerStatus?.running}>
            {schedulerAction === "start" ? "Starting..." : "Start Scheduler"}
          </button>
          <button
            className="secondary-button"
            onClick={() => runSchedulerAction("stop")}
            disabled={schedulerAction !== null || !schedulerStatus?.running}
          >
            {schedulerAction === "stop" ? "Stopping..." : "Stop Scheduler"}
          </button>
        </div>

        {schedulerStatus && (
          <>
            <ul className="kv-list">
              <li><span>Timezone</span><strong>{schedulerStatus.timezone}</strong></li>
              <li><span>Job Count</span><strong>{schedulerStatus.job_count}</strong></li>
              <li><span>Next Run</span><strong>{schedulerStatus.next_run_time ? new Date(schedulerStatus.next_run_time).toLocaleString() : "N/A"}</strong></li>
            </ul>

            <h3 className="linkedin-subtitle">Configured Jobs & Cadence</h3>
            {schedulerStatus.jobs.length === 0 ? (
              <p>No scheduler jobs loaded yet.</p>
            ) : (
              <ul className="activity-list">
                {schedulerStatus.jobs.map((job) => (
                  <li key={job.job_id}>
                    <strong>{job.name}</strong>
                    <span>{job.trigger}</span>
                    <small>Next: {job.next_run_time ? new Date(job.next_run_time).toLocaleString() : "N/A"}</small>
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </section>

      <section className="panel">
        <h2>Recent Activity</h2>
        {activity.length === 0 ? (
          <p>No activity yet. Run a quick action to get started.</p>
        ) : (
          <ul className="activity-list">
            {activity.slice(0, 8).map((item) => (
              <li key={item.id}>
                <strong>{item.action}</strong>
                <span>{item.result}</span>
                <small>{item.timestamp}</small>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
