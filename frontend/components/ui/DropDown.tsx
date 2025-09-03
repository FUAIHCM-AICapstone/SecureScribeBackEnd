import React, { useState, useRef, useEffect } from 'react';

interface Option {
  value: string;
  label: string;
  className?: string; // Add custom className support
}
interface CustomSelectProps {
  options: Option[];
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  className?: string;
  buttonClassName?: string;
  variant?: 'outline' | 'solid';
  displayLabel?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  disabled?: boolean;
  optionClassName?: string; // NEW
  fullWidth?: boolean; // NEW
}

const CustomSelect = ({
  options,
  value,
  onChange,
  placeholder,
  className = '',
  buttonClassName = '',
  variant = 'outline',
  displayLabel,
  leftIcon,
  rightIcon,
  disabled = false,
  optionClassName = '', // NEW
  fullWidth = false, // NEW
}: CustomSelectProps) => {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // click ngoài để đóng
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const selectedLabel = options.find((o) => o.value === value)?.label;
  const hasLabel = !!(displayLabel || selectedLabel || placeholder);

  // Style for button
  const baseBtn =
    'w-full rounded-lg px-4 py-2 h-11 text-left focus:outline-none focus:ring-2 focus:ring-[var(--accent-color)] font-semibold transition';
  const outlineBtn =
    'bg-[var(--surface-color)] border-[2px] border-[var(--primary-color)] text-[var(--primary-color)]';
  const solidBtn =
    'bg-[var(--primary-color)] text-white border-[2px] border-[var(--primary-color)]';
  const btnStyle = `${baseBtn} ${variant === 'solid' ? solidBtn : outlineBtn} ${buttonClassName}`;

  return (
    <div className={`relative ${className}`} ref={ref}>
      <button
        onClick={() => !disabled && setOpen((o) => !o)}
        className={
          btnStyle + (disabled ? ' opacity-60 cursor-not-allowed' : '')
        }
        disabled={disabled}
        tabIndex={disabled ? -1 : 0}
        aria-disabled={disabled}
      >
        <span className="flex items-center justify-between w-full">
          {leftIcon && (
            <span className="mr-2 flex-shrink-0 flex items-center">
              {leftIcon}
            </span>
          )}
          <span className="flex-1 truncate text-left">
            {displayLabel || selectedLabel || placeholder}
          </span>
          {rightIcon && (
            <span className={hasLabel ? "ml-2 flex-shrink-0 flex items-center" : "flex-shrink-0 flex items-center"}>
              {rightIcon}
            </span>
          )}
        </span>
      </button>

      {open && !disabled && (
        <ul className={`absolute z-10 mt-1 ${fullWidth ? 'w-full' : ''} overflow-auto rounded-lg bg-[var(--background-color)] shadow-lg scrollbar-thin scrollbar-thumb-[var(--primary-color)] scrollbar-track-[var(--surface-color)] hover:scrollbar-thumb-[var(--accent-color)]`}>
          {options.map((opt) => (
            <button
              type="button"
              key={opt.value}
              onClick={() => {
                onChange(opt.value);
                setOpen(false);
              }}
              className={`w-full text-left cursor-pointer px-4 py-2 transition
                ${opt.value === value
                  ? 'bg-[var(--background-color)] text-[var(--primary-color)] font-bold'
                  : 'hover:font-bold text-[var(--primary-color)]'
                }
                ${opt.className || optionClassName || ''}
              `}
              role="option"
              aria-selected={opt.value === value}
            >
              {opt.label}
            </button>
          ))}
        </ul>
      )}
    </div>
  );
};

export default CustomSelect;
