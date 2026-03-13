interface BreadcrumbItem {
  label: string;
  onClick?: () => void;
}

interface Props {
  items: BreadcrumbItem[];
}

export default function Breadcrumb({ items }: Props) {
  if (items.length <= 1) return null;

  return (
    <nav className="breadcrumb">
      {items.map((item, i) => {
        const isLast = i === items.length - 1;
        return (
          <span key={i} className="breadcrumb-segment">
            {item.onClick && !isLast ? (
              <button className="breadcrumb-link" onClick={item.onClick}>
                {item.label}
              </button>
            ) : (
              <span className={isLast ? "breadcrumb-current" : ""}>{item.label}</span>
            )}
            {!isLast && <span className="breadcrumb-sep">/</span>}
          </span>
        );
      })}
    </nav>
  );
}
