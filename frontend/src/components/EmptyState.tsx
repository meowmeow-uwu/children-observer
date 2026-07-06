import React from "react";

interface EmptyStateProps {
  icon: string;
  title: string;
  description: string;
  action?: React.ReactNode;
}

export const EmptyState: React.FC<EmptyStateProps> = ({ icon, title, description, action }) => {
  return (
    <div className="flex flex-col items-center justify-center text-center p-8 bg-surface-container-lowest border border-outline-variant/30 rounded-2xl max-w-md mx-auto my-8">
      <div className="w-16 h-16 rounded-full bg-surface-container-low text-outline flex items-center justify-center mb-4">
        <span className="material-symbols-outlined text-[32px]">{icon}</span>
      </div>
      <h3 className="text-lg font-bold text-on-surface mb-1">{title}</h3>
      <p className="text-sm text-on-surface-variant mb-6 leading-relaxed">{description}</p>
      {action && <div className="w-full flex justify-center">{action}</div>}
    </div>
  );
};
export default EmptyState;
