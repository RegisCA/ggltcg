/**
 * Reusable Button Component
 * 
 * Provides consistent styling, accessibility, and touch targets across the application.
 * All variants are WCAG AA compliant for contrast.
 */

import React from 'react';

export interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  children: React.ReactNode;
  onClick?: () => void;
  className?: string;
  type?: 'button' | 'submit';
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  disabled = false,
  children,
  onClick,
  className = '',
  type = 'button',
}) => {
  // Base styles for all buttons
  const baseStyles = 'font-bold rounded-lg transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-yellow-400';
  
  // Variant styles
  const variantStyles = {
    primary: 'bg-game-highlight text-white hover:bg-red-600',
    secondary: 'bg-gray-600 text-white hover:bg-gray-500',
    ghost: 'bg-transparent text-white border-2 border-gray-500 hover:bg-gray-700 hover:border-gray-400',
    danger: 'bg-red-600 text-white hover:bg-red-700',
  };
  
  // Size styles (lg must meet 44x44px touch target minimum)
  const sizeStyles = {
    sm: 'px-3 py-1.5 text-sm min-h-[36px]',
    md: 'px-4 py-2 text-base min-h-[40px]',
    lg: 'px-6 py-3 text-lg min-h-[44px] min-w-[44px]',
  };
  
  // Disabled styles
  const disabledStyles = disabled
    ? 'opacity-50 cursor-not-allowed pointer-events-none'
    : '';
  
  const combinedClassName = `
    ${baseStyles}
    ${variantStyles[variant]}
    ${sizeStyles[size]}
    ${disabledStyles}
    ${className}
  `.trim();
  
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={combinedClassName}
    >
      {children}
    </button>
  );
};
