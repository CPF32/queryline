import Icon from "@/components/icons/Icon";
import { useEffect, useId, useRef, useState } from "react";

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface SelectProps {
  value: string;
  onChange: (value: string) => void;
  options: SelectOption[];
  placeholder?: string;
  disabled?: boolean;
  id?: string;
  className?: string;
  "aria-label"?: string;
  fullWidth?: boolean;
  size?: "sm" | "md";
}

export default function Select({
  value,
  onChange,
  options,
  placeholder = "Select…",
  disabled = false,
  id,
  className = "",
  "aria-label": ariaLabel,
  fullWidth = false,
  size = "md",
}: SelectProps) {
  const generatedId = useId();
  const triggerId = id ?? generatedId;
  const rootRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);

  const selected = options.find((option) => option.value === value);
  const displayLabel = selected?.label ?? placeholder;

  useEffect(() => {
    if (!open) {
      return;
    }
    const close = (event: MouseEvent | KeyboardEvent) => {
      if (event instanceof KeyboardEvent && event.key !== "Escape") {
        return;
      }
      if (event instanceof MouseEvent && rootRef.current?.contains(event.target as Node)) {
        return;
      }
      setOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", close);
    };
  }, [open]);

  const handleSelect = (nextValue: string) => {
    onChange(nextValue);
    setOpen(false);
  };

  return (
    <div
      ref={rootRef}
      className={`app-select app-select--${size}${fullWidth ? " app-select--full" : ""}${open ? " app-select--open" : ""}${disabled ? " app-select--disabled" : ""}${className ? ` ${className}` : ""}`}
    >
      <button
        type="button"
        id={triggerId}
        className="app-select__trigger"
        aria-label={ariaLabel}
        aria-haspopup="listbox"
        aria-expanded={open}
        disabled={disabled}
        onClick={() => {
          if (!disabled) {
            setOpen((current) => !current);
          }
        }}
      >
        <span className={`app-select__value${selected ? "" : " app-select__value--placeholder"}`}>
          {displayLabel}
        </span>
        <Icon name="chevron-down" size={size === "sm" ? 14 : 16} className="app-select__chevron" />
      </button>

      {open && (
        <ul className="app-select__menu" role="listbox" aria-labelledby={triggerId}>
          {options.map((option) => {
            const isSelected = option.value === value;
            return (
              <li key={option.value} role="presentation">
                <button
                  type="button"
                  role="option"
                  aria-selected={isSelected}
                  className={`app-select__option${isSelected ? " app-select__option--selected" : ""}`}
                  disabled={option.disabled}
                  onClick={() => handleSelect(option.value)}
                >
                  {option.label}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
