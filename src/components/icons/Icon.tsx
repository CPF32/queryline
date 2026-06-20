import type { SVGAttributes } from "react";
import { clientTheme } from "@/theme/clientTheme.config";

export type IconName =
  | "sun"
  | "moon"
  | "chat"
  | "database"
  | "settings"
  | "plus"
  | "chevron-down"
  | "chevron-left"
  | "chevron-right"
  | "arrow-left"
  | "arrow-up"
  | "more"
  | "thumbs-up"
  | "thumbs-down"
  | "send"
  | "mic"
  | "archive"
  | "restore"
  | "trash"
  | "sql"
  | "eye"
  | "eye-off"
  | "sign-out";

interface IconProps extends SVGAttributes<SVGSVGElement> {
  name: IconName;
  size?: number;
}

const STROKE = clientTheme.icons.strokeWidth;

export default function Icon({
  name,
  size = clientTheme.icons.defaultSize,
  className,
  ...rest
}: IconProps) {
  const shared = {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    "aria-hidden": rest["aria-hidden"] ?? true,
    className,
    ...rest,
  };

  switch (name) {
    case "sun":
      return (
        <svg {...shared}>
          <circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth={STROKE} />
          <path
            d="M12 3v2M12 19v2M4.5 4.5l1.4 1.4M18.1 18.1l1.4 1.4M3 12h2M19 12h2M4.5 19.5l1.4-1.4M18.1 5.9l1.4-1.4"
            stroke="currentColor"
            strokeWidth={STROKE}
            strokeLinecap="round"
          />
        </svg>
      );

    case "moon":
      return (
        <svg {...shared}>
          <path
            d="M20 14.5A8.5 8.5 0 0 1 8.5 3 6.5 6.5 0 1 0 20 14.5Z"
            stroke="currentColor"
            strokeWidth={STROKE}
            strokeLinejoin="round"
          />
        </svg>
      );

    case "chat":
      return (
        <svg {...shared}>
          <path
            d="M5 6.5A2.5 2.5 0 0 1 7.5 4h9A2.5 2.5 0 0 1 19 6.5v7A2.5 2.5 0 0 1 16.5 16H11l-3.5 3v-3H7.5A2.5 2.5 0 0 1 5 13.5v-7Z"
            stroke="currentColor"
            strokeWidth={STROKE}
            strokeLinejoin="round"
          />
          <path
            d="M9 9.5h6M9 12.5h3.5"
            stroke="currentColor"
            strokeWidth={STROKE}
            strokeLinecap="round"
          />
        </svg>
      );

    case "database":
      return (
        <svg {...shared}>
          <ellipse cx="12" cy="6" rx="7" ry="2.5" stroke="currentColor" strokeWidth={STROKE} />
          <path
            d="M5 6v5c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5V6M5 11v5c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5v-5"
            stroke="currentColor"
            strokeWidth={STROKE}
            strokeLinejoin="round"
          />
        </svg>
      );

    case "settings":
      return (
        <svg {...shared}>
          <circle cx="12" cy="12" r="2.75" stroke="currentColor" strokeWidth={STROKE} />
          <path
            d="M12 3v2.2M12 18.8V21M3 12h2.2M18.8 12H21M5.6 5.6l1.55 1.55M16.85 16.85l1.55 1.55M5.6 18.4l1.55-1.55M16.85 7.15l1.55-1.55"
            stroke="currentColor"
            strokeWidth={STROKE}
            strokeLinecap="round"
          />
        </svg>
      );

    case "plus":
      return (
        <svg {...shared}>
          <path
            d="M12 5v14M5 12h14"
            stroke="currentColor"
            strokeWidth={STROKE}
            strokeLinecap="round"
          />
        </svg>
      );

    case "chevron-down":
      return (
        <svg {...shared}>
          <path
            d="M6 9l6 6 6-6"
            stroke="currentColor"
            strokeWidth={STROKE}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );

    case "chevron-left":
      return (
        <svg {...shared}>
          <path
            d="M15 6l-6 6 6 6"
            stroke="currentColor"
            strokeWidth={STROKE}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );

    case "chevron-right":
      return (
        <svg {...shared}>
          <path
            d="M9 6l6 6-6 6"
            stroke="currentColor"
            strokeWidth={STROKE}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );

    case "arrow-left":
      return (
        <svg {...shared}>
          <path
            d="M11 6L5 12l6 6M5 12h14"
            stroke="currentColor"
            strokeWidth={STROKE}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );

    case "arrow-up":
      return (
        <svg {...shared}>
          <path
            d="M12 19V5M12 5l-4 4M12 5l4 4"
            stroke="currentColor"
            strokeWidth={STROKE}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );

    case "more":
      return (
        <svg {...shared}>
          <circle cx="6" cy="12" r="1.25" fill="currentColor" />
          <circle cx="12" cy="12" r="1.25" fill="currentColor" />
          <circle cx="18" cy="12" r="1.25" fill="currentColor" />
        </svg>
      );

    case "thumbs-up":
      return (
        <svg {...shared}>
          <path
            d="M7 11v8a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2v-3a3 3 0 0 0-3-3h-3l2-5.5a1.5 1.5 0 0 0-3-.5l-3.5 7.5h-3a2 2 0 0 0-2 2"
            stroke="currentColor"
            strokeWidth={STROKE}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );

    case "thumbs-down":
      return (
        <svg {...shared}>
          <path
            d="M17 13v-8a2 2 0 0 0-2-2h-6a2 2 0 0 0-2 2v3a3 3 0 0 0 3 3h3l-2 5.5a1.5 1.5 0 0 0 3 .5l3.5-7.5h3a2 2 0 0 0 2-2"
            stroke="currentColor"
            strokeWidth={STROKE}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );

    case "send":
      return (
        <svg {...shared}>
          <path
            d="M4 12l16-7-7 16-2-7-7-2Z"
            stroke="currentColor"
            strokeWidth={STROKE}
            strokeLinejoin="round"
          />
        </svg>
      );

    case "mic":
      return (
        <svg {...shared}>
          <rect
            x="9"
            y="4"
            width="6"
            height="11"
            rx="3"
            stroke="currentColor"
            strokeWidth={STROKE}
          />
          <path
            d="M6 11a6 6 0 0 0 12 0M12 17v3"
            stroke="currentColor"
            strokeWidth={STROKE}
            strokeLinecap="round"
          />
        </svg>
      );

    case "archive":
      return (
        <svg {...shared}>
          <path
            d="M4 7h16v12a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7Z"
            stroke="currentColor"
            strokeWidth={STROKE}
            strokeLinejoin="round"
          />
          <path
            d="M8 7V5a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2M9 12h6"
            stroke="currentColor"
            strokeWidth={STROKE}
            strokeLinecap="round"
          />
        </svg>
      );

    case "restore":
      return (
        <svg {...shared}>
          <path
            d="M4 12a8 8 0 1 0 2.3-5.7M4 7v5h5"
            stroke="currentColor"
            strokeWidth={STROKE}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );

    case "trash":
      return (
        <svg {...shared}>
          <path
            d="M5 7h14M9 7V5.5A1.5 1.5 0 0 1 10.5 4h3A1.5 1.5 0 0 1 15 5.5V7M8 7l.75 12a1 1 0 0 0 1 .9h4.5a1 1 0 0 0 1-.9L16 7"
            stroke="currentColor"
            strokeWidth={STROKE}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );

    case "sql":
      return (
        <svg {...shared}>
          <path
            d="M8 6h8M8 12h5M8 18h8"
            stroke="currentColor"
            strokeWidth={STROKE}
            strokeLinecap="round"
          />
          <path
            d="M5 4v16"
            stroke="currentColor"
            strokeWidth={STROKE + 0.5}
            strokeLinecap="round"
            opacity="0.5"
          />
        </svg>
      );

    case "eye":
      return (
        <svg {...shared}>
          <path
            d="M2.5 12.5s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z"
            stroke="currentColor"
            strokeWidth={STROKE}
            strokeLinejoin="round"
          />
          <circle cx="12" cy="12.5" r="2.75" stroke="currentColor" strokeWidth={STROKE} />
        </svg>
      );

    case "eye-off":
      return (
        <svg {...shared}>
          <path
            d="M3 4.5 20.5 22M7.8 8.1A4.2 4.2 0 0 0 7 12.5c0 2.3 2.2 4.2 5 4.2 1.2 0 2.3-.4 3.1-1"
            stroke="currentColor"
            strokeWidth={STROKE}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d="M10.2 5.4A9.8 9.8 0 0 1 12 5c3.8 0 6.8 2.2 8.5 4.5a11.2 11.2 0 0 1 1.8 3"
            stroke="currentColor"
            strokeWidth={STROKE}
            strokeLinecap="round"
          />
          <path
            d="M6.5 14.8A9.6 9.6 0 0 1 5 12.5c0-1.1.3-2.1.8-3"
            stroke="currentColor"
            strokeWidth={STROKE}
            strokeLinecap="round"
          />
        </svg>
      );

    case "sign-out":
      return (
        <svg {...shared}>
          <path
            d="M10 7V5.5A1.5 1.5 0 0 1 11.5 4h6A1.5 1.5 0 0 1 19 5.5v13A1.5 1.5 0 0 1 17.5 20h-6A1.5 1.5 0 0 1 10 18.5V17"
            stroke="currentColor"
            strokeWidth={STROKE}
            strokeLinejoin="round"
          />
          <path
            d="M14 12H4M7 9l-3 3 3 3"
            stroke="currentColor"
            strokeWidth={STROKE}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );
  }
}
