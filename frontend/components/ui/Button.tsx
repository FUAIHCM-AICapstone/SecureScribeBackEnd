import React from 'react';

interface ButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  icon?: React.ReactElement;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  type?: 'button' | 'submit' | 'reset';
  className?: string;
  disabled?: boolean;
}

const Button: React.FC<ButtonProps> = ({
  children,
  onClick,
  icon,
  leftIcon,
  rightIcon,
  type = 'button',
  className = '',
  disabled = false,
}) => (
  <button
    type={type}
    onClick={onClick}
    className={`custom-button ${disabled ? 'disabled' : ''} ${className}`}
    disabled={disabled}
  >
    {leftIcon && <span className="custom-button-icon mr-2">{leftIcon}</span>}
    {icon && <span className="custom-button-icon">{icon}</span>}
    {children}
    {rightIcon && <span className="custom-button-icon ml-2">{rightIcon}</span>}
  </button>
);

export default Button;
