import { useMemo, useState } from "react";

import { API_BASE_URL } from "./api/client";
import { Header } from "./components/Header";
import { Sidebar } from "./components/Sidebar";
import { DashboardPage } from "./pages/DashboardPage";
import { GmailPage } from "./pages/GmailPage";
import { JobsPage } from "./pages/JobsPage";
import { LinkedInPage } from "./pages/LinkedInPage";
import { PageKey } from "./pages/pageTypes";
import { RunsLogsPage } from "./pages/RunsLogsPage";
import { SettingsPage } from "./pages/SettingsPage";
import { ActivityItem } from "./types/api";

export default function App() {
  const [page, setPage] = useState<PageKey>("dashboard");
  const [activity, setActivity] = useState<ActivityItem[]>([]);

  function addActivity(entry: Omit<ActivityItem, "id" | "timestamp">) {
    setActivity((prev) => [
      {
        id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
        timestamp: new Date().toLocaleString(),
        ...entry,
      },
      ...prev,
    ]);
  }

  const content = useMemo(() => {
    if (page === "dashboard") {
      return <DashboardPage onAddActivity={addActivity} activity={activity} />;
    }
    if (page === "jobs") {
      return <JobsPage onAddActivity={addActivity} />;
    }
    if (page === "linkedin") {
      return <LinkedInPage />;
    }
    if (page === "gmail") {
      return <GmailPage onAddActivity={addActivity} />;
    }
    if (page === "settings") {
      return <SettingsPage />;
    }
    return <RunsLogsPage />;
  }, [page, activity]);

  return (
    <div className="app-shell">
      <Sidebar activePage={page} onChangePage={setPage} />
      <div className="main-shell">
        <Header page={page} />
        <div className="api-banner">Backend: <code>{API_BASE_URL}</code></div>
        <main>{content}</main>
      </div>
    </div>
  );
}
