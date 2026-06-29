import { cn } from '@/lib/utils';
import type { SensorStatus } from '@/types/api';

const COLORS: Record<SensorStatus, string> = {
  normal: 'bg-normal',
  warning: 'bg-warning',
  critical: 'bg-critical',
  offline: 'bg-offline',
};

export function StatusDot({ status, className }: { status: SensorStatus; className?: string }) {
  return (
    <span className={cn('relative inline-flex size-2.5', className)} aria-hidden="true">
      {status === 'critical' && (
        <span className="absolute inline-flex size-full animate-ping rounded-full bg-critical opacity-60 motion-reduce:hidden" />
      )}
      <span className={cn('relative inline-flex size-2.5 rounded-full', COLORS[status])} />
    </span>
  );
}
