import React from "react";

interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = "Có lỗi xảy ra",
  message,
  onRetry
}) => {
  return (
    <div className="flex flex-col items-center justify-center p-8 bg-error-container/20 border border-error/20 rounded-2xl max-w-md mx-auto my-8 text-center">
      <div className="w-14 h-14 rounded-full bg-error/10 text-error flex items-center justify-center mb-4">
        <span className="material-symbols-outlined text-[30px] fill">warning</span>
      </div>
      <h3 className="text-md font-bold text-on-error-container mb-1">{title}</h3>
      <p className="text-sm text-error mb-6 leading-relaxed">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-5 py-2.5 bg-error text-white font-semibold text-sm rounded-lg hover:bg-error/90 transition-all flex items-center gap-2 shadow-sm focus:outline-none"
        >
          <span className="material-symbols-outlined text-[18px]">refresh</span>
          Thử lại
        </button>
      )}
    </div>
  );
};
export default ErrorState;
