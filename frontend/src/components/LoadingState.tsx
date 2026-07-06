import React from "react";

interface LoadingStateProps {
  message?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({ message = "Đang tải dữ liệu..." }) => {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center">
      <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin mb-4"></div>
      <p className="text-sm font-medium text-on-surface-variant animate-pulse">{message}</p>
    </div>
  );
};
export default LoadingState;
