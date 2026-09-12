import React from 'react';
import { Link } from 'react-router-dom';

interface EmptyStateProps {
  icon: string;
  title: string;
  description: string;
  actionText?: string;
  actionLink?: string;
  onAction?: () => void;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  actionText,
  actionLink,
  onAction,
}) => {
  return (
    <div className="p-16 text-center flex flex-col items-center justify-center gap-3 bg-surface-container-lowest border border-outline/30 shadow-sm">
      <span className="material-symbols-outlined text-4xl text-outline-variant">{icon}</span>
      <h3 className="font-semibold text-base text-on-surface font-heading">{title}</h3>
      <p className="text-xs text-on-surface-variant max-w-md leading-relaxed">{description}</p>
      {actionText && (
        <div className="mt-2">
          {actionLink ? (
            <Link
              to={actionLink}
              className="px-4 py-2 text-xs font-semibold bg-primary text-on-primary hover:bg-primary-container transition-colors shadow-sm inline-block"
            >
              {actionText}
            </Link>
          ) : (
            <button
              onClick={onAction}
              className="px-4 py-2 text-xs font-semibold bg-primary text-on-primary hover:bg-primary-container transition-colors shadow-sm"
            >
              {actionText}
            </button>
          )}
        </div>
      )}
    </div>
  );
};
