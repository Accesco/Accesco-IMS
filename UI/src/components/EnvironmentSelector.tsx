import { useMemo } from 'react';
import { getAllEnvironments } from '../services/environment';

interface EnvironmentSelectorProps {
  currentEnvId: string;
  onChange: (envId: string) => void;
}

export default function EnvironmentSelector({
  currentEnvId,
  onChange,
}: EnvironmentSelectorProps) {
  const environments = useMemo(() => getAllEnvironments(), []);

  return (
    <select
      value={currentEnvId}
      onChange={(e) => onChange(e.target.value)}
      className="rounded-md border border-edge bg-surface-raised px-3 py-1.5 text-sm text-txt outline-none transition-colors hover:border-zinc-600 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30 dark:border-edge dark:bg-surface-raised"
    >
      {environments.map((env) => (
        <option key={env.id} value={env.id}>
          {env.name}
        </option>
      ))}
    </select>
  );
}
