export default function LoadingState() {
  return (
    <div className="flex items-center justify-center py-12">
      <div className="flex flex-col items-center gap-3">
        <div className="relative h-8 w-8">
          <div className="absolute inset-0 rounded-full border-2 border-edge border-edge" />
          <div className="absolute inset-0 animate-spin rounded-full border-2 border-transparent border-t-indigo-500" />
        </div>
        <span className="text-sm text-txt-muted dark:text-txt-sec">
          Sending request…
        </span>
      </div>
    </div>
  );
}
