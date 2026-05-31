interface Props {
  zh: string;
  en: string;
}

/** Bilingual panel header — visual only */
export default function PanelTitle({ zh, en }: Props) {
  return (
    <div className="panel-title">
      <h2>{zh}</h2>
      <span className="panel-subtitle">{en}</span>
    </div>
  );
}
