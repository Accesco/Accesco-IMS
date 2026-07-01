interface EmptyStateProps {
  title?: string;
  message?: string;
  icon?: string;
}

export default function EmptyState({
  title = 'No endpoint selected',
  message = 'Select a module and endpoint from the sidebar to begin testing.',
  icon = '🔌',
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <span className="mb-4 text-4xl">{icon}</span>
      <h3 className="mb-2 text-lg font-semibold text-txt-sec dark:text-txt-sec">
        {title}
      </h3>
      <p className="max-w-sm text-sm text-txt-muted dark:text-txt-muted">
        {message}
      </p>
    </div>
  );
}
