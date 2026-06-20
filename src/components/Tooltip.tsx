import type { ReactElement } from "react";

interface TooltipProps {
  label: string;
  side?: "right" | "top";
  children: ReactElement;
}

export default function Tooltip({ label, side = "right", children }: TooltipProps) {
  return (
    <span className={`tooltip tooltip--${side}`}>
      {children}
      <span className="tooltip__bubble" role="tooltip">
        {label}
      </span>
    </span>
  );
}
