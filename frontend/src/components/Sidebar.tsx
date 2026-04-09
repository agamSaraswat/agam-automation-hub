import { PageKey } from "../pages/pageTypes";

type SidebarProps = {
  activePage: PageKey;
  onChangePage: (page: PageKey) => void;
};

const NAV_ITEMS: Array<{ key: PageKey; label: string }> = [
  { key: "dashboard", label: "Dashboard" },
  { key: "jobs", label: "Jobs" },
  { key: "linkedin", label: "LinkedIn" },
  { key: "gmail", label: "Gmail" },
  { key: "settings", label: "Settings" },
  { key: "runs", label: "Runs / Logs" },
];

export function Sidebar({ activePage, onChangePage }: SidebarProps) {
  return (
    <aside className="sidebar">
      <div className="brand">Agam Hub</div>
      <nav>
        {NAV_ITEMS.map((item) => (
          <button
            key={item.key}
            className={`nav-button ${activePage === item.key ? "active" : ""}`}
            onClick={() => onChangePage(item.key)}
          >
            {item.label}
          </button>
        ))}
      </nav>
    </aside>
  );
}
