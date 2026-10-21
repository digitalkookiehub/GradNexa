import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { BarList } from './BarList';

describe('BarList', () => {
  it('shows a visible label and number for every bar and exposes progress elements', () => {
    render(
      <BarList
        ariaLabel="Levels"
        max={10}
        items={[
          { key: 'a', label: 'Beginner', value: 4, valueText: '4 student(s)' },
          { key: 'b', label: 'Not scored', value: 0, valueText: '0 student(s)' },
        ]}
      />,
    );
    const list = screen.getByRole('list', { name: 'Levels' });
    expect(list).toHaveTextContent('Beginner');
    expect(list).toHaveTextContent('4 student(s)');
    expect(list).toHaveTextContent('Not scored');
    const bar = screen.getByLabelText('Beginner: 4 student(s)') as HTMLProgressElement;
    expect(bar.value).toBe(4);
    expect(bar.max).toBe(10);
  });

  it('clamps values above max and tolerates a zero max', () => {
    render(<BarList ariaLabel="x" max={0} items={[{ key: 'a', label: 'A', value: 5, valueText: '5' }]} />);
    const bar = screen.getByLabelText('A: 5') as HTMLProgressElement;
    expect(bar.max).toBe(1);
    expect(bar.value).toBe(1);
  });
});
