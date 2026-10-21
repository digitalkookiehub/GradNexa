import { Button } from '@/components/ui/button';

interface GoalToggleProps {
  roleName: string;
  isGoal: boolean;
  disabled?: boolean;
  onToggle: () => void;
}

export function GoalToggle({ roleName, isGoal, disabled = false, onToggle }: GoalToggleProps) {
  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={onToggle}
      disabled={disabled}
      aria-pressed={isGoal}
      aria-label={isGoal ? `Remove ${roleName} from my goals` : `Add ${roleName} to my goals`}
      title={isGoal ? 'Remove from my goals' : 'Add to my goals'}
    >
      <span aria-hidden="true" className="text-lg leading-none">
        {isGoal ? '★' : '☆'}
      </span>
    </Button>
  );
}
