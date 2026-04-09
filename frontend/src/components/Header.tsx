import { PageKey, PAGE_LABELS } from "../pages/pageTypes";

type HeaderProps = {
  page: PageKey;
  onRefresh?: () => void;
};

export function Header({ page, onRefresh }: HeaderProps) {
  return (
    <header className="top-header">
      <div>
        <h1>{PAGE_LABELS[page]}</h1>
        <p>Automation dashboard</p>
      </div>
      {onRefresh && (
        <button className="secondary-button" onClick={onRefresh}>
          Refresh
        </button>
      )}
    </header>
  );
}
