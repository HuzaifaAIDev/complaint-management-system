import React from "react";
import { Link } from "react-router-dom";
import { ChevronRight } from "lucide-react";

export interface Crumb {
  label: string;
  to?: string;
}

export default function Breadcrumbs({ items }: { items: Crumb[] }) {
  return (
    <nav className="breadcrumbs" aria-label="Breadcrumb">
      {items.map((item, i) => {
        const isLast = i === items.length - 1;
        return (
          <span key={i} className="breadcrumb-item">
            {item.to && !isLast ? (
              <Link to={item.to}>{item.label}</Link>
            ) : (
              <span aria-current={isLast ? "page" : undefined} className={isLast ? "breadcrumb-current" : ""}>{item.label}</span>
            )}
            {!isLast && <ChevronRight size={13} className="breadcrumb-sep" />}
          </span>
        );
      })}
    </nav>
  );
}
